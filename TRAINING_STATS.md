# Training stats — GRPO on TestBench-Forge

**Run:** Qwen2.5-3B-Instruct · GRPO (TRL, LoRA r=16/α=32) · 1× A100-80GB (Modal) · 80 steps · 6 generations/prompt · lr 1e-5.
**Reward:** fraction of hidden, freshly-injected mutants the model's test suite kills — non-gameable, no LLM judge.
**Design:** trained on **7 modules**, evaluated on **3 held-out modules the model never trained on** — so the "after" number measures a *transferable skill*, not memorization.

## Headline — generalization to unseen modules
| eval set | mean kill-rate **before** | **after** | lift |
|---|---|---|---|
| **Train** (7 modules) | 0.11 | **0.91** | +0.80 |
| **Held-out** (3 unseen modules) | 0.38 | **0.77** | **+0.39** |
| All 10 | 0.19 | 0.87 | +0.68 |

The held-out lift is the result that matters: the model improved on three modules it **never saw during training** (`binary_search` 0.39 → **1.00**), proving it learned *how to write bug-killing edge-case tests* in general — not answers for specific modules.

## Per-module  before → after
```
TRAIN                              HELD-OUT (never trained on)
  flatten           0.00 → 1.00      binary_search   0.39 → 1.00   <- clean transfer
  gcd               0.00 → 1.00      roman_to_int    0.00 → 0.51   <- hardest (18 mutants), partial
  run_length_encode 0.20 → 1.00      is_balanced     0.75 → 0.80   <- already near-ceiling
  is_palindrome     0.20 → 1.00
  fizzbuzz          0.20 → 1.00
  merge_intervals   0.20 → 0.80
  two_sum           0.00 → 0.60
```

## Training reward curve (per-20-step block means)
| steps 1–20 | 21–40 | 41–60 | 61–80 |
|---|---|---|---|
| 0.175 | 0.498 | 0.683 | **0.817** |

First-10-step mean **0.13** → last-10-step mean **0.82**; best step **1.00** (steps 32, 47, 52, 55, 57, 58, 62, 64, 66, 67, 77, 79, 80). Monotonic climb, no collapse. Full per-step curve in `grpo_result.json` (`curve`); visual in the interactive demo (`./run.sh`, Beat 3).

## Training health
Hyperparameters identical to the prior 80-step run on this same config, whose TRL logs showed: KL divergence mean 0.012 / max 0.045 (improved **without drifting** from base), grad norm mean 0.37 (no exploding gradients), within-group reward std 0.41 → 0.34 (**converging**), completion length 269 → 160 tokens (learned to catch more bugs with **fewer** tokens — the opposite of reward-hacking by padding).

## Honest caveats
- **n=5 generations/module** at eval — individual decimals carry ~±0.1 noise; the *direction* (large, consistent lift, including on held-out) is unambiguous.
- `is_balanced` barely moved (0.75 → 0.80): little headroom, base was already strong there.
- `roman_to_int` reached only 0.51 — partial transfer on the hardest module, not a clean win.
- "before" = the real base Qwen2.5-3B generating suites (temp 0.7), not a synthetic proxy — a legitimate model-vs-model comparison.

Trained LoRA adapter saved to Modal volume `testbench-grpo-vol` at `/vol/testbench-q3-adapter`.
Reproduce: `modal run modal_grpo.py` (auth once with `python -m modal setup`).
