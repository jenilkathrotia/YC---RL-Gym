"""GRPO training of a forked open model on TestBench-Forge, via HUD.

Loop: sample G rollouts per module (agent writes a test suite; reward = hidden-mutant
kill rate) -> hud.TrainingClient.step() runs GRPO (importance-sampling, advantages
normalized within each module's group) -> periodically eval -> repeat. The gateway serves
the model's current (in-place advancing) head, so each round samples from the latest weights.

Writes:
  train_log.jsonl    — append-only event log (baseline, each step, each eval)
  train_progress.json— latest curve + per-module numbers (safe to read mid-run)
  results.json       — {module: {base, trained}} for demo.py (written at the end)

Usage:
  python train_rl.py --smoke           # 1 round, 3 modules — validate the loop
  python train_rl.py                   # full run (defaults below)
"""
from __future__ import annotations

import argparse
import asyncio
import inspect
import json
import os
import sys
import time
import traceback

DIR = os.path.dirname(os.path.abspath(__file__))
ENVFILE = DIR + "/env.py"
sys.path.insert(0, DIR)

from hud.settings import settings          # noqa: E402
from hud.agents import create_agent        # noqa: E402
from hud.eval.taskset import Taskset        # noqa: E402
from hud import LocalRuntime                # noqa: E402
import hud                                  # noqa: E402
import env                                  # noqa: E402  (forge_testbench)
import testbench                            # noqa: E402


async def _maybe_await(x):
    return await x if inspect.isawaitable(x) else x


def _has_train_data(run) -> bool:
    if getattr(run, "trace_id", None):
        return True
    try:
        return bool(run.trace.collect(lambda s: getattr(s, "sample", None)))
    except Exception:
        return False


async def eval_per_module(agent, modules, group, timeout):
    """Return {module: mean reward over `group` rollouts}. Sequential (HUD caps active sessions)."""
    out = {}
    for m in modules:
        try:
            task = env.forge_testbench(module_id=m)
            job = await task.run(agent, runtime=LocalRuntime(ENVFILE), group=group,
                                 max_concurrent=group, rollout_timeout=timeout)
            runs = [r for rs in job.results.values() for r in rs]
            out[m] = round(sum(r.reward for r in runs) / len(runs), 4) if runs else 0.0
        except Exception:
            out[m] = 0.0   # infra hiccup (e.g. tinker 503) -> count as 0, keep going
    return out


async def sample_round(agent, modules, group, max_concurrent, timeout):
    """Sample `group` rollouts per module; return runs as contiguous per-module groups."""
    ts = Taskset("tb-train", [env.forge_testbench(module_id=m) for m in modules])
    job = await ts.run(agent, runtime=LocalRuntime(ENVFILE), group=group,
                       max_concurrent=max_concurrent, rollout_timeout=timeout)
    grouped = []
    for _key, runs in job.results.items():
        valid = [r for r in runs if _has_train_data(r)]
        if len(valid) >= group:
            grouped.extend(valid[:group])     # exactly `group` per module -> divisible
    return grouped


async def main(args):
    modules = list(testbench.MODULES) if args.modules == "all" else args.modules.split(",")
    train_agent = create_agent(
        args.slug,
        completion_kwargs={
            "max_tokens": args.max_tokens,
            "temperature": args.temp_train,
            "extra_body": {"return_token_ids": True},  # capture token-ids+logprobs for GRPO
        },
        max_steps=1,
    )
    eval_agent = create_agent(
        args.slug, completion_kwargs={"max_tokens": args.max_tokens, "temperature": args.temp_eval}, max_steps=1)
    tc = hud.TrainingClient(args.slug, api_key=settings.api_key)

    logf = open(DIR + "/train_log.jsonl", "a")

    def record(obj):
        obj["t"] = time.strftime("%H:%M:%S")
        logf.write(json.dumps(obj) + "\n")
        logf.flush()
        print(obj, flush=True)

    record({"event": "start", "slug": args.slug, "modules": modules, "rounds": args.rounds,
            "group": args.group, "lr": args.lr})

    base = await eval_per_module(eval_agent, modules, args.eval_group, args.rollout_timeout)
    base_mean = round(sum(base.values()) / len(base), 4)
    record({"event": "baseline", "mean": base_mean, "per_module": base})
    curve = [{"round": 0, "eval_mean": base_mean}]

    completed = 0
    attempts = 0
    while completed < args.rounds and attempts < args.rounds * 6:
        attempts += 1
        try:
            grouped = await sample_round(train_agent, modules, args.group, args.max_concurrent, args.rollout_timeout)
            if not grouped:
                record({"event": "round_skip", "attempt": attempts, "reason": "no complete groups (infra/503?)"})
                await asyncio.sleep(45)  # back off; tinker capacity may free up
                continue
            train_mean = round(sum(r.reward for r in grouped) / len(grouped), 4)
            res = await _maybe_await(
                tc.step(grouped, learning_rate=args.lr, group_size=args.group))
            completed += 1
            rnd = completed
            record({"event": "step", "round": rnd, "n": len(grouped), "train_mean": train_mean,
                    "result": str(res)[:160]})
            if rnd % args.eval_every == 0:
                ev = await eval_per_module(eval_agent, modules, args.eval_group, args.rollout_timeout)
                em = round(sum(ev.values()) / len(ev), 4)
                curve.append({"round": rnd, "eval_mean": em})
                record({"event": "eval", "round": rnd, "mean": em, "per_module": ev})
                json.dump({"base": base, "latest": ev, "curve": curve, "slug": args.slug},
                          open(DIR + "/train_progress.json", "w"), indent=2)
                # write demo-ready results.json each eval, so a partial run still has real numbers
                json.dump({m: {"base": base.get(m, 0.0), "trained": ev.get(m, 0.0)} for m in modules},
                          open(DIR + "/results.json", "w"), indent=2)
        except Exception as e:
            record({"event": "error", "attempt": attempts, "completed": completed,
                    "err": repr(e)[:220]})
            await asyncio.sleep(45)  # infra error (503/sessions) -> wait for capacity, retry

    final = await eval_per_module(eval_agent, modules, max(args.eval_group, 3), args.rollout_timeout)
    final_mean = round(sum(final.values()) / len(final), 4)
    record({"event": "final", "base_mean": base_mean, "final_mean": final_mean, "per_module": final})
    results = {m: {"base": base.get(m, 0.0), "trained": final.get(m, 0.0)} for m in modules}
    json.dump(results, open(DIR + "/results.json", "w"), indent=2)
    json.dump({"base": base, "final": final, "curve": curve, "slug": args.slug},
              open(DIR + "/train_progress.json", "w"), indent=2)
    record({"event": "done", "base_mean": base_mean, "final_mean": final_mean})


def parse():
    p = argparse.ArgumentParser()
    p.add_argument("--slug", default="testbench-q4")
    p.add_argument("--rounds", type=int, default=30)
    p.add_argument("--group", type=int, default=8)
    p.add_argument("--lr", type=float, default=1e-5)
    p.add_argument("--eval-every", type=int, default=5)
    p.add_argument("--eval-group", type=int, default=2)
    p.add_argument("--max-tokens", type=int, default=16384)
    p.add_argument("--temp-train", type=float, default=1.0)
    p.add_argument("--temp-eval", type=float, default=0.3)
    p.add_argument("--max-concurrent", type=int, default=16)
    p.add_argument("--rollout-timeout", type=float, default=180.0)
    p.add_argument("--modules", default="all")
    p.add_argument("--smoke", action="store_true")
    a = p.parse_args()
    if a.smoke:
        a.rounds, a.group, a.eval_every, a.eval_group = 1, 4, 1, 1
        a.modules = "merge_intervals,is_balanced,two_sum"
    return a


if __name__ == "__main__":
    asyncio.run(main(parse()))
