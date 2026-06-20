# TestBench-Forge — Hackathon Cheat Sheet

**Golden rule:** your API keys are passwords. Never screen-share, screenshot, or post them.

The project lives at `~/Downloads/YC---RL-Gym`. Open Terminal and run this once each session:
```bash
cd ~/Downloads/YC---RL-Gym
source .venv/bin/activate
```

---

## The plan (do it in THIS order)

### 0 — Lock in a guaranteed win first (5 min, no keys)
```bash
python selftest.py      # should end with: weak 0.621 vs thorough 1.000
python demo.py
open demo.html          # click "Run RFT ▶" — bars climb to 100%
```
Now you have a working, presentable project no matter what happens next. Breathe. 🙂

### 1 — Get your keys EARLY (training is slow — start the pipeline ASAP)
- **HUD table** — say: *"Hi, I'm building an RL environment on HUD. Can I get my API key?"*
  ```bash
  hud login
  ```
- **Fireworks table** — say: *"Hi, can I get my $500 credits and API key? And later, can someone help me start an RFT job that uses a reward function I deploy with reward-kit?"*
  ```bash
  export FIREWORKS_API_KEY=fw-PASTE_YOURS_HERE
  ```

### 2 — Get your "before" number
```bash
pip install fireworks-ai reward-kit
python fireworks_baseline.py     # write down the "mean baseline kill_rate"
```

### 3 — Deploy the reward + start training (do this EARLY)
```bash
python build_dataset.py
reward-kit preview --metrics-folders "kill=." --samples dataset.jsonl
reward-kit deploy  --id testbench-forge --metrics-folders "kill=." --force
```
Then **go to the Fireworks booth** and say:
> *"I deployed a reward function with reward-kit. How do I start an RFT job using it, with my `dataset.jsonl` and base model **Qwen2.5-32B**?"*

Let it train in the background. This is the long pole — the earlier you start, the better.

### 4 — While it trains
- Rehearse the demo + the one-line pitch (below).
- Optional, with HUD key: `hud eval tasks.py claude`
- Optional booth check: *"Does my `daytona_runner.py` / `modal_runner.py` use your current SDK?"*

### 5 — After training finishes
- Get the "after" number (Fireworks booth helps point the baseline at your trained model).
- Make `results.json` (ask Claude, or copy this and fill in your two numbers):
  ```json
  { "binary_search": {"base": 0.44, "trained": 0.95} }
  ```
- Rebuild the demo with real numbers:
  ```bash
  python demo.py
  open demo.html
  ```

### 6 — Present
Open `demo.html`, click **"Run RFT ▶"**, and say:
> *"We trained a model to write the test that catches the bug a human reviewer misses — scored only by bugs it has never seen. Base model: 62%. After training: [your number]."*

---

## If something breaks
- Read the terminal message — it usually says what's wrong.
- Paste the red error text to Claude and ask for a fix.
- **Fallback:** Step 0 (the `demo.html` with weak→thorough) always works and still proves the idea. You can present that alone.

## What each sponsor does (for the judges' questions)
- **HUD** — hosts the environment. **Fireworks** — does the training (RFT). **Modal** — GPUs / parallel runs. **Daytona** — safe sandbox for running untrusted code. **Anthropic** — Claude as the comparison baseline.
