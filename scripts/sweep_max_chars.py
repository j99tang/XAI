"""Pick `max_chars` on evidence, not on n=1 (D41).

At 9,000 chars the CIP reporting rule reaches the synthesizer in 0/30 scenarios — the
retrieved block is ~28.6k and blind head-truncation discards the tail it lives in. But a
single probe at 30k, while it recovered the rule, misidentified the device: longer context
buys facts and costs grounding. This measures BOTH effects across caps so the constant is
chosen, not guessed.

Per cell (cap x persona x scenario) it scores two things from the OUTPUT, not the context:
  fact_ok    - did the persona state the fact ITS role owes?
               regulator: the correct CIP clock for that scenario's gold class
               operator : at least one breaker this device actually controls
               data_sci : >=3 of the 5 real SHAP feature names
  device_ok  - is the right device named, and no OTHER RTU asserted?

One retrieval per scenario, sliced at each cap — retrieval is deterministic given the
query, so re-retrieving per cap would only add noise and time.

No API cost. Run: conda run -n xai python scripts/sweep_max_chars.py
"""
from __future__ import annotations

import asyncio, json, re, sys
from pathlib import Path

from lightrag import QueryParam

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from caie.contextualizer.rag import build_rag                      # noqa: E402
from caie.contextualizer.retrieve import (evidence_block, event_to_query,  # noqa: E402
                                          resolve_device)
from caie.contextualizer.synthesize import PERSONAS, synthesize_one  # noqa: E402
from caie.schemas.anomaly_event import AnomalyEvent                # noqa: E402

CAPS = [9000, 15000, 20000, 30000]
SCEN_DIR = ROOT / "experiments" / "scenarios"
OUT = ROOT / "experiments" / "results" / "max_chars_sweep.json"

ONE_HOUR = re.compile(r"\b(one hour|1 hour|within an hour|60 minutes)\b", re.I)
NEXT_DAY = re.compile(r"next calendar day", re.I)
ALL_RTU = re.compile(r"\bRTU-\d\b")


def pick_scenarios(n: int = 5) -> list[dict]:
    """Span the consequence classes and guarantee an ATTEMPT case (the 3-scenario
    stratum where the correct clock is next-calendar-day, not one hour)."""
    recs = [json.loads(p.read_text()) for p in sorted(SCEN_DIR.glob("scenario_*.json"))]
    chosen, seen = [], set()
    for r in recs:
        if "ATTEMPT" in r["gold_facts"]["reportable"]:
            chosen.append(r); seen.add(r["consequence_class"]); break
    for r in recs:
        cls = r["consequence_class"]
        if cls not in seen and len(chosen) < n:
            chosen.append(r); seen.add(cls)
    for r in recs:
        if len(chosen) >= n: break
        if r not in chosen: chosen.append(r)
    return chosen[:n]


def score(out: str, rec: dict, persona: str) -> tuple[bool, bool]:
    g = rec["gold_facts"]
    dev = re.search(r"= (RTU-\d|ENG-WS-\d|SCADA-\d)", g["device"])
    dev = dev.group(1) if dev else ""
    named = set(ALL_RTU.findall(out))
    device_ok = bool(dev) and dev in out and not (named - {dev})

    if persona == "regulator":
        rep = g["reportable"]
        if "ATTEMPT" in rep:      fact_ok = bool(NEXT_DAY.search(out))
        elif "NOT report" in rep: fact_ok = bool(re.search(r"not report|no.{0,12}obligation", out, re.I))
        else:                     fact_ok = bool(ONE_HOUR.search(out))
    elif persona == "operator":
        brs = re.findall(r"BR-\d+-\d+", g["device"])
        fact_ok = any(b in out for b in brs)
    else:
        names = [f["name"] for f in rec["anomaly_event"]["top_features"]]
        fact_ok = sum(n in out for n in names) >= 3
    return fact_ok, device_ok


async def main() -> None:
    recs = pick_scenarios()
    print(f"scenarios: {[r['scenario_id'] for r in recs]}")
    print(f"caps: {CAPS} x {len(PERSONAS)} personas x {len(recs)} scenarios "
          f"= {len(CAPS)*len(PERSONAS)*len(recs)} generations\n", flush=True)

    rag = await build_rag()
    rows = []
    for rec in recs:
        ev = AnomalyEvent.from_dict(rec["anomaly_event"])
        block = await rag.aquery(event_to_query(ev), param=QueryParam(
            mode="hybrid", only_need_context=True, top_k=12, chunk_top_k=12)) or ""
        head = f"{resolve_device(ev.dst_ip)}\n\n{evidence_block(ev)}\n\n"
        for cap in CAPS:
            ctx = head + block[:cap]
            for persona in PERSONAS:
                out = synthesize_one(ctx, persona)
                fact_ok, device_ok = score(out, rec, persona)
                rows.append({"scenario": rec["scenario_id"], "cap": cap, "persona": persona,
                             "ctx_chars": len(ctx), "words": len(out.split()),
                             "fact_ok": fact_ok, "device_ok": device_ok})
                print(f"  {rec['scenario_id']} cap={cap:<6} {persona:15} "
                      f"fact={'Y' if fact_ok else '.'} device={'Y' if device_ok else '.'}",
                      flush=True)

    OUT.write_text(json.dumps(rows, indent=1))
    print(f"\n=== fact_ok / device_ok by cap x persona ({len(recs)} scenarios) ===")
    print(f"{'cap':>7} " + "".join(f"{p:>22}" for p in PERSONAS) + f"{'BOTH':>12}")
    for cap in CAPS:
        cells, both = [], []
        for p in PERSONAS:
            sub = [r for r in rows if r["cap"] == cap and r["persona"] == p]
            f = sum(r["fact_ok"] for r in sub) / len(sub)
            d = sum(r["device_ok"] for r in sub) / len(sub)
            cells.append(f"{f:.0%} fact / {d:.0%} dev".rjust(22))
            both += [r["fact_ok"] and r["device_ok"] for r in sub]
        print(f"{cap:>7} " + "".join(cells) + f"{sum(both)/len(both):>11.0%}")
    print(f"\nfull rows -> {OUT}")
    print("Pick the cap maximising BOTH: facts reaching the output without losing grounding.")


if __name__ == "__main__":
    asyncio.run(main())
