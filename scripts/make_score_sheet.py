"""Write the human-scoring worksheet as two files you can open and fill in.

  experiments/results/human_score_sheet.md   <- read this (gold + narrative + anchors)
  experiments/results/human_scores.csv       <- type your scores here

Blind by construction: run and tier are omitted from the sheet, and the judge's scores
appear nowhere in either file. Item ids are opaque so you cannot infer the model.
"""
from __future__ import annotations
import csv, importlib.util, json, textwrap
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
spec = importlib.util.spec_from_file_location("hs", ROOT / "scripts/human_score.py")
hs = importlib.util.module_from_spec(spec); spec.loader.exec_module(hs)

items = hs.sample()
md = ["# CPAS human-scoring worksheet",
      "",
      "Score each narrative against the **gold facts shown with it** — not against",
      "power-systems knowledge. The simulator already made the physics judgement.",
      "Record scores in `human_scores.csv`, then run:",
      "",
      "```",
      "conda run -n xai python scripts/human_score.py --report",
      "```",
      "",
      "Run and tier are deliberately hidden so you cannot infer which model wrote it.",
      "Some narratives are four-line alerts that score ~1 on everything — that is expected.",
      "", "---", ""]

for dim, (title, anchor) in hs.ANCHORS.items():
    md += [f"**{dim} — {title}**", "", "```", anchor, "```", ""]
md += ["---", ""]

rows, keymap = [], {}
for n, (run, sid, tier, persona) in enumerate(items, 1):
    gold = json.loads((ROOT / f"experiments/scenarios/{sid}.json").read_text())["gold_facts"]
    nar = (ROOT / f"experiments/results/{run}/{sid}_{tier}_{persona}.txt").read_text().strip()
    md += [f"## Item {n:02d} — persona: **{persona}**", "",
           f"*Asked for:* {hs.EXPECT[persona]}".replace("\n", " "), "",
           "**Gold facts**", ""]
    for k in ("device", "attack_class", "physical_consequence", "reportable"):
        md.append(f"- **{k}**: {gold[k]}")
    md += ["", "**Narrative**", "", "```", nar, "```", "",
           f"`item {n:02d}` → D __  C __  A __  R __  H __", "", "---", ""]
    # OPAQUE id in the CSV: a visible "ollama-llama3.1-8b|...|C|..." key would tell you
    # which model wrote it and which tier it is, destroying the blinding while you score.
    rows.append({"item": f"{n:02d}", "persona": persona,
                 "D": "", "C": "", "A": "", "R": "", "H": ""})
    keymap[f"{n:02d}"] = f"{run}|{sid}|{tier}|{persona}"

(ROOT / "experiments/results/human_score_sheet.md").write_text("\n".join(md))
csv_path = ROOT / "experiments/results/human_scores.csv"
with open(csv_path, "w", newline="") as f:
    w = csv.DictWriter(f, fieldnames=["item", "persona", "D", "C", "A", "R", "H"])
    w.writeheader()
    for r in rows:
        w.writerow({k: r[k] for k in w.fieldnames})
(ROOT / "experiments/results/.human_score_keymap.json").write_text(json.dumps(keymap, indent=1))
print(f"sheet : {ROOT / 'experiments/results/human_score_sheet.md'}")
print(f"csv   : {csv_path}")
print(f"{len(items)} items; fill D,C,A,R (1-5) and H (0/1) in the csv.")
