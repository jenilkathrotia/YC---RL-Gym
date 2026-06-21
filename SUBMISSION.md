# TestBench-Forge — submission

**An RL gym that trains a model to write the test suite that catches the most bugs — scored by a reward we proved you can't game.**

> **Thesis.** Recursive self-improvement is bottlenecked on *trustworthy verification*. As agents do more autonomous work, the binding constraint isn't generation — it's a grader you can trust. An LLM-judge reward is itself gameable, so the only durable RL signal is an **execution oracle**. We built one for test-writing, **hardened it by attacking it ourselves**, and showed the verification skill it trains **generalizes to tasks it never saw**.

**One sentence:** We built an RL reward we couldn't game — we broke it ourselves with a frame‑walk exploit that faked a perfect score, fixed it so all 12 attacks now score zero — and the test‑writing skill it trains generalizes to modules it never saw (held-out mean 0.23 → 0.79, reproducible at n=16; `binary_search` 0.31 → 0.93).

**Track fit:** Agentic Collaboration (the pytest gym we present) · **wedge:** the same gym ports to chip design — Verilog testbenches where mutants become injected RTL faults and a kill is a failing assertion in simulation.

---

## The loop
1. The agent sees a module + its **reference implementation**.
2. It writes a **pytest-style test suite** (`test_*` functions).
3. The harness runs the suite against a **hidden pool of mutants** (buggy variants of the reference).
4. **Reward = #mutants killed / #mutants**, gated by the suite first passing the reference **and** behavior-equivalent refactors (the over-specification gate). **No LLM judge — a pure execution oracle.**

---

## 1 · Honest oracle  *(verifiable in 5 seconds, zero setup)*
A judge can clone the repo and run it with **system `python3` — no venv, no pip install, no API key, no GPU:**

```bash
git clone https://github.com/jenilkathrotia/YC---RL-Gym && cd YC---RL-Gym
python3 selftest.py        # lazy suite 0.621 · thorough 1.000 · assert-False 0.000
```

A lazy happy-path suite scores **0.621**; a thorough edge-case suite **1.000**; `assert False` or a no-test suite → **0.000** (fails the reference gate). Every module reaches a clean 1.0 ceiling because mutants are differentially filtered to the **non-equivalent (killable)** set. The reward is a subprocess execution oracle — nothing to argue with.

## 2 · Proven non-gameable  *(we attacked our own reward)*
The suite is **untrusted code**. Most RL-environment submissions never test whether their reward is gameable. We did — and **broke it**: a content-free suite using `operator.attrgetter("f_back")` walked the call stack, read the hidden reference source, and faked a perfect **1.0** with no real tests.

We fixed it: an **import allowlist** (a denylist is a sieve), **frame isolation** (the impl source is deleted before the suite runs), and a **nonce-authenticated verdict** (a forged `{"passed": true}` ledger is ignored). Two independent red-team passes now find no bypass (≈9/10 confidence).

```bash
python3 security_checks.py   # 12 adversarial attacks all 0.000 · legit suite 1.000
```

Forged ledger · `SystemExit` short-circuit · `inspect`/`operator.attrgetter` frame-walk · `__subclasses__` gadget · `import os`/`import testbench` oracle · `__del__` finalizer · `eval` — **all score 0**, while legitimate suites are unaffected. `python3 stage_a_checks.py` adds 5 more regression tests.

## 3 · Generalizing verifier  *(the RSI signal)*
We trained Qwen2.5-3B with **GRPO on a single Modal A100** (LoRA r=16) on **7 modules**, then evaluated on **3 modules it never trained on**:

| eval set | mean kill-rate **before → after** |
|---|---|
| Train (7 modules), in-training n=5 | 0.11 → **0.91** |
| **Held-out (3 unseen) — reproducible, n=16** | **0.23 → 0.79** |
| `binary_search` (held-out) | 0.31 → **0.93** |
| `roman_to_int` (held-out) | 0.13 → **0.71** |
| `is_balanced` (held-out) | 0.25 → **0.73** |

The skill — *write correct, boundary/edge-case tests that kill bugs* — **transferred to tasks it never saw**. That's the RSI thesis made concrete: you don't label outputs, you train the **grader**, and the grading generalizes. (KL ≈ 0.012; completion length 269 → 160 tokens — it caught *more* bugs with *fewer* tokens, the opposite of reward-hacking by padding.) Reproduce: `modal run modal_grpo.py` to train; `modal run dump_suites.py` to reload the saved adapter and re-measure.

**How it's measured (honest):** the held-out figure is the **reproducible** one — reload the saved adapter and sample **n=16 per module** (the in-training n=5 eval agreed on the trained side: 0.38 → 0.77). The per-suite spread is real and informative: the **base** model passes the correctness gate on only ~2–5 of 16 tries — it keeps writing a *wrong* assertion the gate rejects — while the **trained** model passes on 12–15 and writes thorough suites. See the literal base-vs-trained suites in the interactive demo (**`./run.sh`** → `web/`).

---

## Sponsor stack (honest status)
| sponsor | role | status |
|---|---|---|
| **Modal** | serverless A100 — **where the GRPO run actually trained**; adapter lives on a Modal volume | ✅ **core, real** |
| **HUD** | the `forge_testbench` env template; frontier baselines via the HUD gateway (Qwen3-8B **0.90**, Claude **0.60**) | ✅ env + baselines |
| **Fireworks** | Eval-Protocol RFT handoff wired (`reward.py`, `testbench_eval_protocol.py`); best-of-1 inference baseline **0.487** (incl. gate failures) | 🟡 wired; RFT launch blocked on billing |
| **Anthropic** | Claude as the frontier baseline in the before/after | 🔵 baseline |
| **Daytona** | `daytona_runner.py` for sandboxing untrusted suites (`REWARDFORGE_RUNNER=daytona`) | ⚪ present, not yet exercised |

> Training landed on **Modal** because HUD's training backend hit capacity limits and Fireworks RFT was billing-blocked — so the verified result is Modal-led. We present what's real.

## Why it's a strong RL environment (not an eval)
- **Multi-signal, verifiable reward** with a clean execution oracle — no LLM judge anywhere.
- **Non-gameable, and we proved it** — you cannot fake killing a bug you've never seen, and you cannot read the hidden bug out of the harness (we tried).
- **Infinite data** — AST mutation operators × unlimited modules, differentially filtered to a clean killable ceiling.
- **Generalizes** — a transferable verification skill, not module-specific memorization.

## Run it
```bash
git clone https://github.com/jenilkathrotia/YC---RL-Gym && cd YC---RL-Gym
python3 selftest.py          # the signal (no setup)
python3 security_checks.py   # the cheat-proof (no setup)
python3 stage_a_checks.py    # regression suite (no setup)
# event-day (needs deps/keys/GPU): modal run modal_grpo.py
```
