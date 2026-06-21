"""Fireworks reward-kit adapter for TestBench-Forge.

Wraps `testbench.score_suite` as a reward-kit reward function so the SAME scorer that
evaluates also trains the model via RFT/GRPO — guaranteeing the before/after lift is
measured against the identical signal.

reward-kit signature (verified against docs.fireworks.ai, June 2026):
    @reward_function
    def fn(messages, ground_truth=None, **kwargs) -> EvaluateResult(score, reason, metrics)
  - model output  = messages[-1]["content"]   (the generated test suite)
  - per-sample id = ground_truth["module_id"] (from the dataset row's ground_truth_for_eval)

This file imports cleanly even if reward-kit is NOT installed (offline shims), so the core
scoring glue can be unit-tested without the SDK. Install for real training:
    pip install reward-kit
Deploy:  reward-kit deploy --id testbench-forge --metrics-folders "kill=." --force
"""
from __future__ import annotations

import families
import testbench

try:
    from reward_kit import reward_function
    from reward_kit.models import EvaluateResult, MetricResult
    _HAS_REWARD_KIT = True
except Exception:  # offline / not installed -> minimal shims so this module still imports
    _HAS_REWARD_KIT = False
    from dataclasses import dataclass, field

    @dataclass
    class MetricResult:  # type: ignore[no-redef]
        score: float = 0.0
        success: bool = False
        reason: str = ""

    @dataclass
    class EvaluateResult:  # type: ignore[no-redef]
        score: float = 0.0
        reason: str = ""
        metrics: dict = field(default_factory=dict)


def _content(msg) -> str:
    if isinstance(msg, dict):
        return msg.get("content") or ""
    return getattr(msg, "content", "") or ""


def compute_score(messages, ground_truth):
    """Pure scoring core (no reward-kit types) — returns (score, reason). Unit-testable."""
    suite = families.extract_code(_content(messages[-1]) if messages else "")
    module_id = (ground_truth or {}).get("module_id")
    if module_id not in testbench.MODULES:
        return 0.0, f"unknown module_id: {module_id!r}"
    rate, info = testbench.score_suite(module_id, suite)
    if not info.get("gate"):
        return 0.0, f"gate failed: {info.get('reason', 'suite did not pass reference')}"
    denom = info.get("denominator", "raw")
    if denom == "ms_star":
        return rate, (
            f"MS* killed {info.get('ms_star_killed', 0)}/{info.get('ms_star_total', 0)} "
            f"behavioral mutant clusters; raw killed {info.get('killed', 0)}/"
            f"{info.get('mutants', 0)}"
        )
    return rate, f"killed {info['killed']}/{info['mutants']} hidden mutants"


def _evaluate(messages, ground_truth=None, **kwargs) -> EvaluateResult:
    score, reason = compute_score(messages, ground_truth)
    return EvaluateResult(
        score=score,
        reason=reason,
        metrics={"mutant_kill_rate": MetricResult(score=score, success=score > 0.0, reason=reason)},
    )


# The deployable reward function. With reward-kit installed it gains validation + .deploy().
evaluate = reward_function(_evaluate) if _HAS_REWARD_KIT else _evaluate
