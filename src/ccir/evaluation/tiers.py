"""The three ablation tiers (plan §4.2) — the A/B/C evidence that CONTEXT, not
just XAI, drives the improvement.

- Tier A: IDS output only (prediction + confidence). No explanation.
- Tier B: IDS + raw SHAP feature list. XAI but no grounding.
- Tier C: full system — retrieved context + 3 persona narratives.

Each tier writes experiments/results/<scenario>_<tier>_<persona>.txt. Tiers A/B
are the same text for all personas (they have no persona conditioning) — that is
the point: only C is persona-aware.

Run: conda run -n xai python -m ccir.evaluation.tiers
"""
from __future__ import annotations

import asyncio
import json
from pathlib import Path

from ccir.contextualizer.rag import ROOT, build_rag
from ccir.contextualizer.synthesize import PERSONAS, synthesize_all
from ccir.schemas.anomaly_event import AnomalyEvent

SCEN_DIR = ROOT / "experiments" / "scenarios"
OUT = ROOT / "experiments" / "results"


def tier_a(ev: AnomalyEvent) -> str:
    return (f"INTRUSION ALERT\nprediction: {ev.prediction}\n"
            f"confidence: {ev.confidence:.2f}\ndestination: {ev.dst_ip}:{ev.dst_port}")


def tier_b(ev: AnomalyEvent) -> str:
    feats = "\n".join(f"  {f.name}: value={f.value:g}, SHAP={f.shap:+.3f}"
                      for f in ev.top_features)
    return f"{tier_a(ev)}\ntop SHAP features (toward 'attack'):\n{feats}"


async def main() -> None:
    scenarios = sorted(SCEN_DIR.glob("scenario_*.json"))
    rag = await build_rag()
    OUT.mkdir(parents=True, exist_ok=True)

    for path in scenarios:
        rec = json.loads(path.read_text())
        sid = rec["scenario_id"]
        ev = AnomalyEvent.from_dict(rec["anomaly_event"])

        a, b = tier_a(ev), tier_b(ev)
        for persona in PERSONAS:                       # A/B identical across personas
            (OUT / f"{sid}_A_{persona}.txt").write_text(a)
            (OUT / f"{sid}_B_{persona}.txt").write_text(b)

        c = await synthesize_all(ev, rag)              # C: persona-specific
        for persona in PERSONAS:
            (OUT / f"{sid}_C_{persona}.txt").write_text(c[persona])
        print(f"{sid}: A/B/C written ({len(ev.top_features)} features)")

    print(f"\ndone: {len(scenarios)} scenarios x 3 tiers x 3 personas -> {OUT}")


if __name__ == "__main__":
    asyncio.run(main())
