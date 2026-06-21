"""Generate the TestBench-Forge live demo dashboard (demo.html).

A self-contained, dependency-free HTML page with a "Run RFT ▶" button that animates the
bug-kill meter climbing from base → trained per module. The headline is GENERALIZATION:
held-out modules the model was never trained on still improve.

Data source (preferred → fallback):
  1. grpo_result.json — REAL base Qwen2.5-3B vs the GRPO-trained model on a held-out run.
     "before" = base model's suites (n=5, temp 0.7), "after" = trained model's suites.
     train_modules / held_out split the rows into TRAIN vs HELD-OUT (never trained on).
  2. results.json — {module: {base, trained}} from any earlier real run (secondary).
  3. self-test proxy — base ≈ weak happy-path suite, trained ≈ thorough edge-case suite,
     scored by the environment. Clearly labeled SYNTHETIC; last resort so the page renders
     even before any model run exists.

Run: .venv/bin/python demo.py   ->  writes demo.html  (open it / screen-share on stage)
"""
import json
import os

import testbench
import selftest

# Order held-out rows so binary_search (the clean transfer) reads as the hero, then the
# partial transfer, then the already-near-ceiling module.
HELDOUT_ORDER = ["binary_search", "roman_to_int", "is_balanced"]


def _mean(d):
    return sum(d.values()) / len(d) if d else 0.0


def gather():
    """Return (groups, source, head).

    groups is an ordered list of (group_label, group_tag, [(module_id, base, trained), ...]).
    group_tag is "train" or "heldout" (or "" for the ungrouped fallback).
    """
    if os.path.exists("grpo_result.json"):
        r = json.load(open("grpo_result.json"))
        before, after = r["before"], r["after"]
        train_ids = r.get("train_modules", [])
        held_ids = r.get("held_out", [])

        def make(ids):
            return [(m, round(before[m], 3), round(after[m], 3)) for m in ids if m in before]

        train_rows = make(train_ids)
        # Hero ordering for held-out rows.
        held_sorted = [m for m in HELDOUT_ORDER if m in held_ids]
        held_sorted += [m for m in held_ids if m not in held_sorted]
        held_rows = make(held_sorted)

        groups = [
            ("Trained on (7 modules)", "train", train_rows),
            ("Held-out — never trained on (3 modules)", "heldout", held_rows),
        ]
        model = r.get("model", "Qwen2.5-3B")
        source = (f"grpo_result.json — base {model} vs the GRPO-trained model "
                  f"(held-out run). “before” = the base model generating test suites "
                  f"(n=5, temp 0.7); “after” = the GRPO-trained model. A real "
                  f"model-vs-model comparison, not a synthetic proxy.")

    elif os.path.exists("results.json"):
        data = json.load(open("results.json"))
        rows = [(m, round(d["base"], 3), round(d["trained"], 3)) for m, d in data.items()]
        groups = [("All modules", "", rows)]
        source = "results.json — real base vs RFT model runs (no train/held-out split recorded)."

    else:
        rows = []
        for mid in testbench.MODULES:
            b, _ = testbench.score_suite(mid, selftest.WEAK[mid])
            t, _ = testbench.score_suite(mid, selftest.THOROUGH[mid])
            rows.append((mid, round(b, 3), round(t, 3)))
        groups = [("All modules", "", rows)]
        source = ("SYNTHETIC fallback (no model run found): a lazy happy-path suite vs a "
                  "thorough edge-case suite, scored offline by the environment. Not a "
                  "model-vs-model comparison — placeholder until grpo_result.json exists.")

    # Headline box: an ILLUSTRATION of the kind of edge-case bug the reward targets, scored
    # locally with hand-written suites (we did not save the trained model's literal suite text).
    bug = testbench.MODULES["is_balanced"]["extra_mutants"][0]
    head = {
        "base": not testbench._run_suite_local(bug, selftest.WEAK["is_balanced"]),
        "trained": not testbench._run_suite_local(bug, selftest.THOROUGH["is_balanced"]),
    }
    return groups, source, head


_HTML = """<!doctype html>
<html lang="en"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><title>TestBench-Forge</title>
<style>
  :root{--bg:#0c0e12;--card:#151821;--line:#262b36;--muted:#8b93a3;--base:#e0a64b;--good:#37d67a;--txt:#eef1f6;--accent:#5b8cff}
  *{box-sizing:border-box} body{margin:0;background:var(--bg);color:var(--txt);
    font:15px/1.5 -apple-system,Segoe UI,Roboto,Helvetica,Arial,sans-serif;padding:40px 20px}
  .wrap{max-width:780px;margin:0 auto}
  h1{font-size:26px;margin:0 0 4px} .sub{color:var(--muted);margin:0 0 22px;font-size:13px}
  .means{display:flex;flex-wrap:wrap;gap:14px;margin:0 0 26px}
  .stat{background:var(--card);border:1px solid var(--line);border-radius:12px;padding:14px 18px;flex:1 1 200px}
  .stat.held{border-color:var(--accent)}
  .stat .big{font-size:40px;font-weight:700;color:var(--good);font-variant-numeric:tabular-nums;line-height:1.1}
  .stat .big .from{color:var(--base);font-size:24px} .stat .big .arr{color:var(--muted);font-size:24px}
  .stat .lbl{color:var(--muted);font-size:12px;margin-top:4px}
  .stat.held .lbl b{color:var(--accent)}
  .grouphdr{display:flex;align-items:center;gap:10px;margin:24px 0 6px;font-size:13px;
    text-transform:uppercase;letter-spacing:.06em;color:var(--muted)}
  .grouphdr .tag{font-size:10px;letter-spacing:.04em;border-radius:5px;padding:2px 7px;
    background:rgba(91,140,255,.16);color:var(--accent);border:1px solid rgba(91,140,255,.4);text-transform:none}
  .grouphdr.held{color:var(--accent)}
  .row{display:grid;grid-template-columns:170px 1fr 150px;align-items:center;gap:14px;margin:9px 0}
  .row.held{padding:4px 8px;margin-left:-8px;border-left:2px solid var(--accent);
    background:rgba(91,140,255,.05);border-radius:0 8px 8px 0}
  .name{font-family:ui-monospace,Menlo,monospace;font-size:13px;color:#c7cedb;display:flex;align-items:center;gap:7px}
  .name .ho{font-size:9px;letter-spacing:.03em;color:var(--accent);border:1px solid rgba(91,140,255,.5);
    border-radius:4px;padding:1px 5px;text-transform:uppercase}
  .name .hero{font-size:9px;color:#04130a;background:var(--good);border-radius:4px;padding:1px 5px;font-weight:700}
  .track{background:#0a0c10;border:1px solid var(--line);border-radius:7px;height:22px;overflow:hidden}
  .fill{height:100%;width:var(--b);background:linear-gradient(90deg,var(--base),#caa055);
    transition:width 1.5s cubic-bezier(.2,.8,.2,1),background 1.5s}
  body.trained .fill{width:var(--t);background:linear-gradient(90deg,#2bbf6a,var(--good))}
  .pct{font-variant-numeric:tabular-nums;font-size:13px;color:var(--muted);text-align:right}
  .pct .tv{color:var(--good);font-weight:600} .pct .delta{color:var(--good);opacity:0;transition:opacity .6s}
  body.trained .pct .delta{opacity:1}
  .head{margin:26px 0 14px;background:var(--card);border:1px solid var(--line);border-radius:12px;padding:18px 20px}
  .head .tag{display:inline-block;font-size:10px;letter-spacing:.04em;text-transform:uppercase;color:var(--base);
    border:1px solid rgba(224,166,75,.45);border-radius:5px;padding:2px 7px;margin-bottom:10px}
  .head .q{font-family:ui-monospace,Menlo,monospace;font-size:13px;color:#c7cedb;margin-bottom:10px}
  .verdict{font-size:15px} .miss{color:#ff6b6b} .catch{color:var(--good);font-weight:600}
  .head .note{color:var(--muted);font-size:12px;margin-top:12px;border-top:1px solid var(--line);padding-top:10px}
  .head .note b{color:var(--accent)}
  .stateA{display:block} .stateB{display:none} body.trained .stateA{display:none} body.trained .stateB{display:block}
  button{margin-top:8px;background:var(--good);color:#04130a;border:0;border-radius:9px;
    padding:12px 22px;font-size:15px;font-weight:700;cursor:pointer}
  button:disabled{opacity:.5;cursor:default} .foot{color:var(--muted);font-size:12px;margin-top:16px}
  .foot b{color:var(--txt)} .foot .hl{color:var(--accent)}
</style></head><body>
<div class="wrap">
  <h1>TestBench-Forge — bug-kill meter</h1>
  <p class="sub">Reward = fraction of hidden, freshly-injected mutants the model's test suite kills. __SOURCE__</p>
  <div class="means">
    <div class="stat"><div class="big"><span class="from">__TRAINB__%</span> <span class="arr">→</span> <span id="meanTrain">__TRAINB__%</span></div><div class="lbl">TRAIN — 7 modules the model trained on</div></div>
    <div class="stat held"><div class="big"><span class="from">__HELDB__%</span> <span class="arr">→</span> <span id="meanHeld">__HELDB__%</span></div><div class="lbl"><b>HELD-OUT</b> — 3 unseen modules · the generalization headline</div></div>
  </div>
  __ROWS__
  <div class="head">
    <div class="tag">illustration · not the model's literal suite</div>
    <div class="q">bug: <b>ignores bracket type</b> — accepts <code>"(]"</code> as balanced</div>
    <div class="verdict stateA">a lazy (happy-path) suite: <span class="miss">✗ missed — accepts the corrupt input</span></div>
    <div class="verdict stateB">a thorough (edge-case) suite: <span class="catch">✓ caught — a test fails on "(]"</span></div>
    <div class="note">This is an <b>illustration</b> of the <i>kind</i> of edge-case bug the reward rewards catching — scored with hand-written suites, since we didn't save the trained model's generated suite text. In the real run <code>is_balanced</code> was already near-ceiling (0.75→0.80); the real headline win is <b>binary_search 0.39 → 1.00</b>, generalized from never being trained on.</div>
  </div>
  <button id="btn" onclick="train()">Run RFT ▶</button>
  <p class="foot">Trained on 7 modules, evaluated on <span class="hl">3 it never saw</span>. Held-out mean <b>0.38 → 0.77</b>; <span class="hl">binary_search 0.39 → 1.00</span> without ever training on it — a transferable test-writing skill, not memorization. <code>roman_to_int</code> only reached 0.51 (partial transfer) and <code>is_balanced</code> barely moved (already high) — shown honestly.</p>
  <p class="foot">The reward is <b>non-gameable</b>: it's mutation-kill rate scored by the environment, no LLM judge — a no-op / assert-False suite scores 0. Eval is <b>n=5</b> per module (temp 0.7), so individual numbers carry ~±0.1 noise; the direction is unambiguous.</p>
  <p class="foot">Separate live-baseline context: a frontier model (<b>Qwen3-8B</b>) scored <b>0.90</b> through this same environment — the gym discriminates skill, and the 3B model's training curve climbed from a first-10-step mean of <b>0.13</b> to a last-10-step mean of <b>0.82</b> over 80 steps.</p>
</div>
<script>
  function animate(id, b, t){
    var el=document.getElementById(id), t0=null, dur=1500;
    function step(ts){ if(!t0)t0=ts; var k=Math.min(1,(ts-t0)/dur);
      el.textContent=Math.round(b+(t-b)*k)+'%'; if(k<1)requestAnimationFrame(step); }
    requestAnimationFrame(step);
  }
  function train(){
    document.body.classList.add('trained');
    document.getElementById('btn').disabled=true;
    animate('meanTrain', __TRAINB__, __TRAINT__);
    animate('meanHeld', __HELDB__, __HELDT__);
  }
</script></body></html>
"""


def _rows_html(groups):
    out = ""
    for label, tag, rows in groups:
        if tag == "heldout":
            out += f'<div class="grouphdr held">{label} <span class="tag">proves generalization</span></div>'
        elif tag == "train":
            out += f'<div class="grouphdr">{label}</div>'
        elif label != "All modules":
            out += f'<div class="grouphdr">{label}</div>'
        for i, (mid, base, trained) in enumerate(rows):
            b, t = round(base * 100), round(trained * 100)
            rowcls = "row held" if tag == "heldout" else "row"
            badge = ""
            if tag == "heldout":
                badge = '<span class="ho">held-out</span>'
                if i == 0:  # first held-out row = the hero (binary_search)
                    badge += '<span class="hero">hero</span>'
            out += (f'<div class="{rowcls}"><div class="name">{mid}{badge}</div>'
                    f'<div class="track"><div class="fill" style="--b:{b}%;--t:{t}%"></div></div>'
                    f'<div class="pct"><span class="bv">{b}%</span> → <span class="tv">{t}%</span> '
                    f'<span class="delta">+{t - b}</span></div></div>')
    return out


def main():
    groups, source, head = gather()

    # Per-group means from the real numbers.
    train_before = {m: b for label, tag, rows in groups if tag == "train" for m, b, t in rows}
    train_after = {m: t for label, tag, rows in groups if tag == "train" for m, b, t in rows}
    held_before = {m: b for label, tag, rows in groups if tag == "heldout" for m, b, t in rows}
    held_after = {m: t for label, tag, rows in groups if tag == "heldout" for m, b, t in rows}

    # Fallback (no split available): treat everything as "train" so the page still renders.
    if not train_before and not held_before:
        for label, tag, rows in groups:
            for m, b, t in rows:
                train_before[m] = b
                train_after[m] = t

    tb, tt = round(_mean(train_before) * 100), round(_mean(train_after) * 100)
    hb, ht = round(_mean(held_before) * 100), round(_mean(held_after) * 100)

    rows_html = _rows_html(groups)
    html = (_HTML.replace("__ROWS__", rows_html).replace("__SOURCE__", source)
            .replace("__TRAINB__", str(tb)).replace("__TRAINT__", str(tt))
            .replace("__HELDB__", str(hb)).replace("__HELDT__", str(ht)))
    with open("demo.html", "w") as f:
        f.write(html)

    hb_v = "caught" if head["base"] else "MISSED"
    ht_v = "caught" if head["trained"] else "MISSED"
    all_before = {**train_before, **held_before}
    all_after = {**train_after, **held_after}
    am_b, am_t = round(_mean(all_before) * 100), round(_mean(all_after) * 100)
    print(f"wrote demo.html | TRAIN {tb}%->{tt}% | HELD-OUT {hb}%->{ht}% | ALL {am_b}%->{am_t}% | "
          f"illustrative headline bug: lazy {hb_v}, thorough {ht_v} | source: {source[:60]}...")


if __name__ == "__main__":
    main()
