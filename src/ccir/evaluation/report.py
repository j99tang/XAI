"""Run the judge across all scenarios x tiers x personas and aggregate (plan §4.6).

Produces the CPAS table by persona x tier (expect C > B > A) plus per-tier answer
lengths (the verbosity-bias control from §7.6 #1). Writes JSON + a printed table.

Requires ANTHROPIC_API_KEY. Run: conda run -n xai python -m ccir.evaluation.report
"""
from __future__ import annotations

import json
import os
import statistics
from pathlib import Path

from ccir.evaluation.judge import SCEN_DIR, _client, judge_narrative

ROOT = Path(__file__).resolve().parents[3]
RESULTS = ROOT / "experiments" / "results"
TIERS = ["A", "B", "C"]
PERSONAS = ["operator", "data_scientist", "regulator"]
OUT = RESULTS / "cpas_scores.json"


def main() -> None:
    if not os.environ.get("ANTHROPIC_API_KEY"):
        raise SystemExit("Set ANTHROPIC_API_KEY first:  ! export ANTHROPIC_API_KEY=sk-ant-...")
    client = _client()
    scenarios = sorted(SCEN_DIR.glob("scenario_*.json"))

    rows = []  # one per (scenario, tier, persona)
    for spath in scenarios:
        rec = json.loads(spath.read_text())
        sid, gold = rec["scenario_id"], rec["gold_facts"]
        for tier in TIERS:
            for persona in PERSONAS:
                fp = RESULTS / f"{sid}_{tier}_{persona}.txt"
                if not fp.exists():
                    continue
                narrative = fp.read_text()
                scored = judge_narrative(client, narrative, gold, persona)
                rows.append({"scenario": sid, "kind": rec["kind"], "tier": tier,
                             "persona": persona, "chars": len(narrative), **scored})
                print(f"{sid} {tier} {persona:14} CPAS={scored['cpas']:.2f} "
                      f"(D{scored['D']} C{scored['C']} A{scored['A']} R{scored['R']} H{scored['H']})")

    OUT.write_text(json.dumps(rows, indent=2))

    # aggregate: mean CPAS + mean length by tier x persona
    print("\n=== CPAS by tier x persona (mean; expect C > B > A) ===")
    print(f"{'persona':16} {'A':>18} {'B':>18} {'C':>18}")
    for persona in PERSONAS:
        cells = []
        for tier in TIERS:
            vals = [r["cpas"] for r in rows if r["tier"] == tier and r["persona"] == persona]
            lens = [r["chars"] for r in rows if r["tier"] == tier and r["persona"] == persona]
            cells.append(f"{statistics.mean(vals):.2f} ({int(statistics.mean(lens))}c)" if vals else "-")
        print(f"{persona:16} {cells[0]:>18} {cells[1]:>18} {cells[2]:>18}")
    print("\n(cell = mean CPAS (mean answer length in chars) — length reported per "
          "§7.6 #1 so the comparison isn't length-confounded)")
    print(f"\nfull scores -> {OUT}")


if __name__ == "__main__":
    main()
