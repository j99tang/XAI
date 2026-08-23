"""Run the judge across all scenarios x tiers x personas via the BATCH API and
aggregate (plan §4.6).

Batch API = 50% cheaper than per-call, and these judge calls are independent and
not latency-sensitive — a textbook batch fit. One batch of REPEATS x 135 = 405
requests; results keyed by custom_id (they arrive in any order). Produces the CPAS
table by persona x tier (expect C > B > A) plus per-tier answer lengths (the
verbosity-bias control, §7.6 #1).

custom_id format: "<scenario>__<tier>__<persona>__r<repeat>"

Requires ANTHROPIC_API_KEY. Run: conda run -n xai python -m caie.evaluation.report
Most batches finish in <1h (max 24h); the script polls and blocks until done.
"""
from __future__ import annotations

import json
import os
import statistics
import time
from pathlib import Path

from anthropic.types.message_create_params import MessageCreateParamsNonStreaming
from anthropic.types.messages.batch_create_params import Request

from scipy.stats import wilcoxon

from caie.contextualizer.synthesize import run_tag
from caie.evaluation.judge import (JUDGE_MODEL, LAMBDA, REPEATS, SCEN_DIR, THRESHOLD,
                                    _client, aggregate_runs, assert_independent_of,
                                    cpas, judge_params, parse_scores)
from caie.evaluation.tiers import PERSONAS, TIERS, fingerprint, run_dir

ROOT = Path(__file__).resolve().parents[3]
SEP = "__"


def build_requests(rdir: Path) -> tuple[list[Request], dict[str, dict]]:
    """One Request per (scenario, tier, persona, repeat). Also returns metadata
    keyed by the narrative id (scenario/tier/persona) for aggregation.

    Fails loudly on a stale or incomplete run rather than judging it (D38). Scenario
    ids are positional: after a scenario-set rebuild `scenario_01` is a different
    incident, so a narrative left from an earlier set would be graded against the wrong
    gold facts and score as a confident hallucination. The old code did
    `if not fp.exists(): continue`, which silently dropped missing narratives and still
    printed a full-looking table."""
    manifest_path = rdir / "manifest.json"
    if not manifest_path.exists():
        raise SystemExit(f"{manifest_path} missing — run `python -m caie.evaluation.tiers` first")
    manifest = json.loads(manifest_path.read_text())

    requests, meta, missing, stale = [], {}, [], []
    for spath in sorted(SCEN_DIR.glob("scenario_*.json")):
        rec = json.loads(spath.read_text())
        sid, gold = rec["scenario_id"], rec["gold_facts"]
        if manifest["scenarios"].get(sid) != fingerprint(rec):
            stale.append(sid)
            continue
        for tier in TIERS:
            for persona in PERSONAS:
                fp = rdir / f"{sid}_{tier}_{persona}.txt"
                if not fp.exists() or not fp.stat().st_size:
                    missing.append(fp.name)
                    continue
                narrative = fp.read_text()
                nid = f"{sid}{SEP}{tier}{SEP}{persona}"
                meta[nid] = {"scenario": sid, "kind": rec["kind"],
                             "consequence_class": rec.get("consequence_class", "n/a"),
                             "tier": tier, "persona": persona, "chars": len(narrative)}
                for r in range(REPEATS):
                    requests.append(Request(
                        custom_id=f"{nid}{SEP}r{r}",
                        params=MessageCreateParamsNonStreaming(
                            **judge_params(narrative, gold, persona))))
    if stale:
        raise SystemExit(
            f"{len(stale)} scenario(s) changed since these narratives were generated "
            f"({', '.join(stale[:5])}{'...' if len(stale) > 5 else ''}).\n"
            f"Judging them would grade a narrative against a DIFFERENT incident's gold "
            f"facts. Re-run: python -m caie.evaluation.tiers")
    if missing:
        raise SystemExit(
            f"{len(missing)} narrative(s) missing from {rdir} "
            f"(e.g. {', '.join(missing[:4])}).\nRe-run: python -m caie.evaluation.tiers")
    return requests, meta


def poll_and_collect(client, batch_id: str) -> dict[str, dict]:
    """Poll an EXISTING batch to completion, then return scores keyed by custom_id.
    Safe to call on a batch submitted by a prior (e.g. killed) run — the batch lives
    server-side, so this never resubmits or double-charges."""
    print(f"attached to batch {batch_id} — polling...")
    while True:
        b = client.messages.batches.retrieve(batch_id)
        if b.processing_status == "ended":
            break
        c = b.request_counts
        print(f"  {b.processing_status}: {c.succeeded} done, {c.processing} processing, "
              f"{c.errored} errored", flush=True)
        time.sleep(30)

    scores, errors = {}, 0
    for res in client.messages.batches.results(batch_id):
        if res.result.type == "succeeded":
            # a truncated (max_tokens) response still reports "succeeded" but yields
            # invalid JSON -- don't let one bad row abort collection of an already-paid batch
            try:
                scores[res.custom_id] = parse_scores(res.result.message)
            except (json.JSONDecodeError, StopIteration) as e:
                errors += 1
                print(f"  UNPARSEABLE {res.custom_id}: {type(e).__name__} "
                      f"(stop_reason={res.result.message.stop_reason})")
        else:
            errors += 1
            print(f"  ERROR {res.custom_id}: {res.result.type}")
    if errors:
        print(f"WARNING: {errors}/{len(scores) + errors} requests unusable "
              f"-- rerun with --batch {batch_id} to re-collect without recharging")
    return scores


def paired_test(rows: list[dict], lo: str, hi: str) -> str:
    """Wilcoxon signed-rank, PAIRED BY SCENARIO (D34).

    The unit of analysis is the scenario, not the row: the three personas share a
    scenario and a context block, so treating 3xN rows as independent observations is
    pseudoreplication. We average the personas within a scenario, then pair scenarios
    across tiers."""
    def by_scenario(tier):
        acc = {}
        for r in rows:
            if r["tier"] == tier:
                acc.setdefault(r["scenario"], []).append(r["cpas"])
        return {k: statistics.mean(v) for k, v in acc.items()}
    a, b = by_scenario(lo), by_scenario(hi)
    common = sorted(set(a) & set(b))
    x = [b[k] - a[k] for k in common]
    if len(common) < 6 or all(d == 0 for d in x):
        return f"{hi} vs {lo}: n={len(common)} — too few pairs to test"
    stat, pval = wilcoxon([a[k] for k in common], [b[k] for k in common])
    delta = statistics.mean(x)
    flag = "***" if pval < 0.001 else "**" if pval < 0.01 else "*" if pval < 0.05 else "n.s."
    return (f"{hi} vs {lo}: n={len(common)} pairs, mean Δ={delta:+.3f}, "
            f"W={stat:.1f}, p={pval:.4f} {flag}")


def main() -> None:
    import argparse
    ap = argparse.ArgumentParser()
    ap.add_argument("--batch", help="attach to an existing batch id instead of submitting a new one")
    ap.add_argument("--run", default=None, help="run tag to score (default: current synthesizer)")
    args = ap.parse_args()

    if not os.environ.get("ANTHROPIC_API_KEY"):
        raise SystemExit("Set ANTHROPIC_API_KEY first (see .env)")
    rdir = run_dir(args.run)
    if not rdir.exists():
        raise SystemExit(f"{rdir} not found — run `python -m caie.evaluation.tiers` first")
    manifest = json.loads((rdir / "manifest.json").read_text())
    assert_independent_of(manifest["synth_backend"], manifest["synth_model"])
    out_path = rdir / "cpas_scores.json"
    print(f"run: {rdir.name}  (synthesizer: {manifest['synth_model']}, "
          f"judge: {JUDGE_MODEL})")

    client = _client()
    requests, meta = build_requests(rdir)  # meta (custom_id map) is deterministic
    if not requests:
        raise SystemExit("no tier outputs found — run `python -m caie.evaluation.tiers` first")

    if args.batch:
        batch_id = args.batch  # reconnect to a prior submission — no new charge
    else:
        batch_id = client.messages.batches.create(requests=requests).id
        print(f"submitted batch {batch_id} ({len(requests)} requests)")
    scores = poll_and_collect(client, batch_id)

    # regroup the REPEATS runs per narrative, aggregate (median + cpas + spread)
    rows = []
    for nid, m in meta.items():
        runs = [scores[f"{nid}{SEP}r{r}"] for r in range(REPEATS)
                if f"{nid}{SEP}r{r}" in scores]
        if not runs:
            continue
        rows.append({**m, **aggregate_runs(runs)})

    rows.sort(key=lambda x: (x["scenario"], x["tier"], x["persona"]))
    out_path.write_text(json.dumps(
        {"run_tag": manifest["run_tag"], "synth_model": manifest["synth_model"],
         "judge_model": JUDGE_MODEL,
         "threshold": THRESHOLD, "rows": rows}, indent=2))
    for r in rows:
        print(f"{r['scenario']} {r['tier']} {r['persona']:14} CPAS={r['cpas']:.2f} "
              f"(D{r['D']} C{r['C']} A{r['A']} R{r['R']} H{r['H']})")

    print("\n=== CPAS by tier x persona (mean; expect C > B > A) ===")
    print(f"{'persona':16} {'A':>18} {'B':>18} {'C':>18}")
    for persona in PERSONAS:
        cells = []
        for tier in TIERS:
            vals = [r["cpas"] for r in rows if r["tier"] == tier and r["persona"] == persona]
            lens = [r["chars"] for r in rows if r["tier"] == tier and r["persona"] == persona]
            cells.append(f"{statistics.mean(vals):.2f} ({int(statistics.mean(lens))}c)" if vals else "-")
        print(f"{persona:16} {cells[0]:>18} {cells[1]:>18} {cells[2]:>18}")
    print("\n(cell = mean CPAS (mean answer length in chars) — length per §7.6 #1 so "
          "the comparison isn't length-confounded)")

    # Pass rate: a second headline less sensitive to λ than the mean (D31).
    print(f"\n=== pass rate (raw weighted D/C/A/R >= {THRESHOLD}, before the λ penalty) ===")
    print(f"{'tier':6} {'pass rate':>10} {'mean raw':>10} {'mean CPAS':>10}")
    for tier in TIERS:
        sub = [r for r in rows if r["tier"] == tier]
        if not sub:
            continue
        raw = [r["cpas"] + LAMBDA * r["H"] for r in sub]   # undo the penalty
        print(f"{tier:6} {sum(v >= THRESHOLD for v in raw)/len(raw):>9.0%} "
              f"{statistics.mean(raw):>10.2f} {statistics.mean(r['cpas'] for r in sub):>10.2f}")

    # Significance, paired by scenario — means alone cannot support "A < B < C".
    print("\n=== paired Wilcoxon signed-rank (unit = scenario, personas averaged) ===")
    for lo, hi in (("A", "B"), ("B", "C"), ("A", "C")):
        print("  " + paired_test(rows, lo, hi))

    # D27: can a BINARY detector's output be resolved to the specific attack class at
    # all? Diagnostic only -- never part of CPAS. If this stays low even for tier C and
    # a frontier synthesizer, the lever is a multiclass detector, not a bigger model.
    print("\n=== attack class named correctly (DIAGNOSTIC, not in CPAS) ===")
    print(f"{'tier':6} " + "".join(f"{p:>17}" for p in PERSONAS))
    for tier in TIERS:
        cells = []
        for persona in PERSONAS:
            v = [r["attack_class_correct"] for r in rows
                 if r["tier"] == tier and r["persona"] == persona]
            cells.append(f"{sum(v)/len(v):>16.0%}" if v else f"{'-':>16}")
        print(f"{tier:6} " + "".join(cells))

    # Does context help more where the physics is harder? Only answerable since D37.
    classes = sorted({r["consequence_class"] for r in rows} - {"n/a"})
    if classes:
        print("\n=== mean CPAS by consequence class x tier (D37 stratification) ===")
        print(f"{'class':12} " + "".join(f"{t:>8}" for t in TIERS))
        for cls in classes:
            cells = []
            for tier in TIERS:
                v = [r["cpas"] for r in rows if r["tier"] == tier and r["consequence_class"] == cls]
                cells.append(f"{statistics.mean(v):>8.2f}" if v else f"{'-':>8}")
            print(f"{cls:12} " + "".join(cells))

    print(f"\nfull scores -> {out_path}")


if __name__ == "__main__":
    main()
