#!/usr/bin/env bash
# TestBench-Forge — live demo runner (~90s, 3 beats). Real terminal, no faked inference.
# Beats 1-2 need only system python3 (no venv / key / GPU). Beat 3 opens a pre-rendered page.
# Run from the repo root:   bash run_demo.sh
PY="${PY:-python3}"
pause(){ read -rp $'\n  ── press [enter] ── '; clear; }

clear
echo "════════════════════════════════════════════════════════════"
echo "  BEAT 1 · Honest oracle"
echo "  Reward = fraction of HIDDEN mutants the agent's tests kill."
echo "  No LLM judge. Pure execution. A judge can re-run this now."
echo "════════════════════════════════════════════════════════════"
echo
"$PY" selftest.py
echo
echo "  → lazy suite 0.62 · thorough 1.00 · assert-False 0.00"
pause

echo "════════════════════════════════════════════════════════════"
echo "  BEAT 2 · So we tried to cheat our own reward"
echo "  The 'RED-TEAM killer' below (operator.attrgetter frame-walk)"
echo "  scored a FAKE 1.0 against our first version. We found it and"
echo "  fixed it — import allowlist + frame isolation. Now: all 0."
echo "════════════════════════════════════════════════════════════"
echo
"$PY" security_checks.py
echo
echo "  (git log shows it: commit 0c5dc29 'red-team found a 1.0 bypass')"
pause

echo "════════════════════════════════════════════════════════════"
echo "  BEAT 3 · The verifier generalizes (the RSI signal)"
echo "  Trained on 7 modules with GRPO. Evaluated on 3 it NEVER saw."
echo "  Reproducible (reload the saved adapter, n=16):"
echo "      held-out mean   0.23  →  0.79"
echo "      binary_search   0.31  →  0.93   (never trained on)"
echo "════════════════════════════════════════════════════════════"
echo
echo "  The model's REAL base-vs-trained suites + the reward curve are in the"
echo "  interactive demo. In another terminal:  ./run.sh   (http://localhost:5173)"
echo
echo "  Pitch: you don't label outputs — you train the GRADER,"
echo "         and the grading generalizes. That's the RSI bottleneck."
echo
