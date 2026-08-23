"""The three ablation tiers (plan §4.2) — the A/B/C evidence that CONTEXT, not
just XAI, drives the improvement.

- Tier A: IDS output only (prediction + confidence). No explanation.
- Tier B: IDS + raw SHAP feature list. XAI but no grounding.
- Tier C: full system — retrieved context + 3 persona narratives.

Each tier writes experiments/results/<run_tag>/<scenario>_<tier>_<persona>.txt.
Tiers A/B are the same text for all personas (they have no persona conditioning) —
that is the point: only C is persona-aware.

RUN NAMESPACING (D38). Output is namespaced by `run_tag()` — the synthesizer backend
and model. The §7.7 capability sweep runs N synthesizers; a flat results/ directory has
no model dimension, so each model would silently overwrite the last one's narratives.

STALENESS GUARD (D38). Scenario ids are positional: after a scenario-set rebuild,
`scenario_01` is a DIFFERENT incident. A narrative left on disk from an earlier set
would then be judged against the new gold facts and score as a confident hallucination.
The manifest records a fingerprint of each scenario's gold facts; report.py refuses to
run when a narrative's fingerprint does not match the scenario it claims to explain.

Run:  conda run -n xai python -m caie.evaluation.tiers            # resumes by default
      conda run -n xai python -m caie.evaluation.tiers --fresh    # regenerate all
"""
from __future__ import annotations

import argparse
import asyncio
import hashlib
import json
from datetime import datetime, timezone
from pathlib import Path

from caie.contextualizer.rag import ROOT, build_rag
from caie.contextualizer.retrieve import evidence_block
from caie.contextualizer.synthesize import (PERSONAS, SYNTH_BACKEND, run_tag,
                                            synth_model, synthesize_all)
from caie.schemas.anomaly_event import AnomalyEvent

SCEN_DIR = ROOT / "experiments" / "scenarios"
RESULTS = ROOT / "experiments" / "results"
TIERS = ["A", "B", "C"]


def run_dir(tag: str | None = None) -> Path:
    return RESULTS / (tag or run_tag())


def fingerprint(rec: dict) -> str:
    """Hash of the scenario INPUT a narrative is generated from — the anomaly event.

    Deliberately EXCLUDES `gold_facts`. The synthesizer never sees gold facts; they are
    the judge's answer key. Including them meant a gold revision (D46) invalidated 540
    perfectly valid narratives and demanded ~2 hours of regeneration that would have
    produced byte-identical output. What must trigger regeneration is a change to what
    the model was GIVEN, not to what it is graded against.

    (A gold change still forces a re-JUDGE, but that is report.py's concern and costs
    one batch, not two runs of generation.)"""
    payload = json.dumps(rec["anomaly_event"], sort_keys=True).encode()
    return hashlib.sha256(payload).hexdigest()[:16]


def tier_a(ev: AnomalyEvent) -> str:
    return (f"INTRUSION ALERT\nprediction: {ev.prediction}\n"
            f"confidence: {ev.confidence:.2f}\ndestination: {ev.dst_ip}:{ev.dst_port}")


def tier_b(ev: AnomalyEvent) -> str:
    # Same formatter the tier-C context block uses, so C is a strict superset of B.
    return evidence_block(ev)


async def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--fresh", action="store_true",
                    help="regenerate every narrative instead of resuming")
    args = ap.parse_args()

    scenarios = sorted(SCEN_DIR.glob("scenario_*.json"))
    if not scenarios:
        raise SystemExit(f"no scenarios in {SCEN_DIR} — run scripts/make_fact_sheets.py")

    out = run_dir()
    out.mkdir(parents=True, exist_ok=True)
    print(f"run_tag: {run_tag()}  ({SYNTH_BACKEND} / {synth_model()})\n  -> {out}\n", flush=True)

    manifest_path = out / "manifest.json"
    prior = json.loads(manifest_path.read_text()) if manifest_path.exists() else {}
    prior_fp = prior.get("scenarios", {}) if not args.fresh else {}

    rag = await build_rag()
    manifest = {"run_tag": run_tag(), "synth_backend": SYNTH_BACKEND,
                "synth_model": synth_model(), "personas": PERSONAS, "tiers": TIERS,
                "generated_utc": datetime.now(timezone.utc).isoformat(timespec="seconds"),
                "scenarios": {}}
    generated = skipped = 0

    for path in scenarios:
        rec = json.loads(path.read_text())
        sid, fp = rec["scenario_id"], fingerprint(rec)
        manifest["scenarios"][sid] = fp
        ev = AnomalyEvent.from_dict(rec["anomaly_event"])

        # Tiers A and B are deterministic text -- always cheap to rewrite.
        a, b = tier_a(ev), tier_b(ev)
        for persona in PERSONAS:
            (out / f"{sid}_A_{persona}.txt").write_text(a)
            (out / f"{sid}_B_{persona}.txt").write_text(b)

        # Tier C costs a model call per persona -- resume unless the scenario changed.
        c_files = [out / f"{sid}_C_{persona}.txt" for persona in PERSONAS]
        if (not args.fresh and prior_fp.get(sid) == fp
                and all(f.exists() and f.stat().st_size for f in c_files)):
            skipped += 1
            print(f"{sid}: skip (unchanged)", flush=True)
            continue

        c = await synthesize_all(ev, rag)
        for persona in PERSONAS:
            (out / f"{sid}_C_{persona}.txt").write_text(c[persona])
        generated += 1
        print(f"{sid}: A/B/C written ({len(ev.top_features)} features)", flush=True)
        manifest_path.write_text(json.dumps(manifest, indent=2))  # checkpoint each loop

    # Narratives for scenarios that no longer exist would otherwise be judged later.
    # Compare against the set of filenames we EXPECT, never by parsing a filename back
    # into fields: a persona like "data_scientist" contains the same "_" separator, so
    # splitting "scenario_01_A_data_scientist.txt" yields the wrong scenario id and
    # deletes a file that is perfectly valid.
    expected = {f"{sid}_{tier}_{persona}.txt"
                for sid in manifest["scenarios"] for tier in TIERS for persona in PERSONAS}
    stale = [f for f in out.glob("scenario_*.txt") if f.name not in expected]
    for f in stale:
        f.unlink()

    manifest_path.write_text(json.dumps(manifest, indent=2))
    print(f"\ndone: {len(scenarios)} scenarios x {len(TIERS)} tiers x {len(PERSONAS)} personas"
          f" -> {out}\n  tier C: {generated} generated, {skipped} resumed"
          f"{f', {len(stale)} stale removed' if stale else ''}")


if __name__ == "__main__":
    asyncio.run(main())
