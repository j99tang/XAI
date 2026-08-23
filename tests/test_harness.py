# run: conda run -n xai python tests/test_harness.py   (no API calls, no Ollama)
"""Guards on the evaluation harness (D38). These check the failure paths, because the
two worst bugs here are silent: judging a stale narrative against the wrong incident,
and dropping missing narratives while still printing a full-looking table."""
import asyncio, contextlib, io, json, pathlib, shutil, sys

import ccir.evaluation.tiers as T
from ccir.evaluation.judge import assert_independent_of
from ccir.evaluation.report import build_requests, paired_test

SC = pathlib.Path("experiments/scenarios")
TMP = pathlib.Path("/tmp/ccir_test_harness")
RECS = [json.loads(p.read_text()) for p in sorted(SC.glob("scenario_*.json"))]
assert RECS, "no scenarios -- run scripts/make_fact_sheets.py"
GOOD = {r["scenario_id"]: T.fingerprint(r) for r in RECS}


def fake_run(manifest_scenarios, skip=(), empty=()):
    shutil.rmtree(TMP, ignore_errors=True); TMP.mkdir(parents=True)
    (TMP / "manifest.json").write_text(json.dumps(
        {"run_tag": "t", "synth_backend": "ollama", "synth_model": "llama3.1:8b",
         "scenarios": manifest_scenarios}))
    for r in RECS:
        for tier in T.TIERS:
            for p in T.PERSONAS:
                key = (r["scenario_id"], tier, p)
                if key in skip: continue
                (TMP / f"{r['scenario_id']}_{tier}_{p}.txt").write_text("" if key in empty else "n")
    return TMP


def blocked(**kw) -> bool:
    try:
        build_requests(fake_run(**kw)); return False
    except SystemExit:
        return True


reqs, meta = build_requests(fake_run(GOOD))
assert len(meta) == len(RECS) * len(T.TIERS) * len(T.PERSONAS), len(meta)

# a scenario changed since its narrative was written -> would grade the WRONG incident
assert blocked(manifest_scenarios={**GOOD, "scenario_01": "0" * 16}), "stale not caught"
# a missing or zero-byte narrative -> a partial table that looks complete
assert blocked(manifest_scenarios=GOOD, skip={(RECS[0]["scenario_id"], "C", "regulator")})
assert blocked(manifest_scenarios=GOOD, empty={(RECS[0]["scenario_id"], "C", "operator")})

# the judge must never share a vendor with the synthesizer (§7.6)
try:
    assert_independent_of("openai", "anthropic/claude-opus-4-6"); raise AssertionError("no guard")
except SystemExit:
    pass
assert_independent_of("openai", "openai/gpt-5.4")


def test_resume():
    """tiers.py must resume, regenerate only what changed, and never delete a valid file.

    The regression this pins: personas contain "_" (data_scientist), so parsing a
    filename back into fields mis-identifies the scenario and deletes 90 good
    narratives every run -- which then silently defeats resume."""
    calls = []
    async def fake_synth(ev, rag=None):
        calls.append(ev.flow_id); return {p: "x" for p in T.PERSONAS}
    async def fake_rag(): return None
    orig = (T.synthesize_all, T.build_rag, T.run_dir)
    T.synthesize_all, T.build_rag, T.run_dir = fake_synth, fake_rag, lambda tag=None: TMP
    shutil.rmtree(TMP, ignore_errors=True)
    try:
        def run(argv=()):
            calls.clear(); sys.argv = ["tiers", *argv]
            with contextlib.redirect_stdout(io.StringIO()):
                asyncio.run(T.main())
            return len(calls)

        assert run() == len(RECS), "first run must generate every scenario"
        assert run() == 0, "second run must resume, not regenerate"
        assert run(["--fresh"]) == len(RECS), "--fresh must regenerate"
        run()
        n_files = len(list(TMP.glob("*.txt")))
        assert n_files == len(RECS) * 9, f"{n_files} files, want {len(RECS)*9} -- deletion bug"
        assert sum("data_scientist" in f.name for f in TMP.glob("*.txt")) == len(RECS) * 3

        (TMP / f"{RECS[8]['scenario_id']}_C_data_scientist.txt").unlink()
        assert run() == 1, "a deleted narrative must regenerate exactly its scenario"

        (TMP / "scenario_99_C_operator.txt").write_text("orphan")
        run()
        assert not (TMP / "scenario_99_C_operator.txt").exists(), "orphan must be removed"
    finally:
        T.synthesize_all, T.build_rag, T.run_dir = orig
        shutil.rmtree(TMP, ignore_errors=True)


def test_tier_monotonicity():
    """A subset B subset C-context. The ablation only means what it claims if each tier
    strictly ADDS evidence: A = alert, B = A + SHAP, C = B + retrieved context.

    Regression pinned: the SHAP features were used to build the retrieval query but never
    passed to the synthesizer, so tier C had LESS evidence than tier B. The data-scientist
    persona was asked which features drove the prediction, was never told, and invented
    them -- which would have scored as 'context makes the data scientist worse'."""
    from ccir.contextualizer.retrieve import evidence_block
    from ccir.schemas.anomaly_event import AnomalyEvent
    for rec in RECS[:5]:
        ev = AnomalyEvent.from_dict(rec["anomaly_event"])
        a, b = T.tier_a(ev), T.tier_b(ev)
        assert b.startswith(a), "tier B must contain tier A"
        assert evidence_block(ev) == b, "tier C's context must contain tier B verbatim"
        for f in ev.top_features:
            assert f.name in b, f"{f.name} missing from the evidence given to B and C"


def test_persona_queries():
    """§11.1: every persona must have a retrieval intent, and the intents must differ.
    A missing key is a KeyError at run time, mid-batch; an accidental copy-paste would
    silently restore the shared-query behaviour D42 removed."""
    from ccir.contextualizer.retrieve import PERSONA_INTENT, event_to_query
    from ccir.schemas.anomaly_event import AnomalyEvent
    assert set(PERSONA_INTENT) == set(T.PERSONAS), PERSONA_INTENT.keys()
    assert len(set(PERSONA_INTENT.values())) == len(T.PERSONAS), "intents must be distinct"
    ev = AnomalyEvent.from_dict(RECS[0]["anomaly_event"])
    qs = {p: event_to_query(ev, p) for p in T.PERSONAS}
    assert len(set(qs.values())) == len(T.PERSONAS), "per-persona queries must differ"
    # the regulator query must actually ask for the fact that was missing 30/30 (D41)
    assert "CIP-008" in qs["regulator"] and "next calendar day" in qs["regulator"]
    for q in qs.values():                       # incident evidence stays in every query
        assert ev.dst_ip in q and ev.top_features[0].name in q


def test_truncation_guard_exists():
    """A truncated narrative must RAISE, never be written to disk.

    It would otherwise be a valid-looking .txt: complete-file checks pass, the manifest
    fingerprint matches, and the judge scores it as a BAD EXPLANATION rather than a
    BROKEN RUN. On reasoning models this is easy to hit, since internal reasoning tokens
    share the output budget with the answer. (The live end-to-end check is in
    scripts/, since this test must not require an API key or a running Ollama.)"""
    import inspect
    from ccir.contextualizer import synthesize as S
    assert issubclass(S.TruncatedNarrative, Exception)
    src = inspect.getsource(S._complete)
    assert "max_tokens=MAX_OUTPUT_TOKENS" in src, "openai path must pin max_tokens"
    assert "num_predict" in src, "ollama path must pin num_predict"
    assert src.count("TruncatedNarrative") >= 3, "both backends + empty-content must guard"
    assert 'finish_reason == "length"' in src and 'done_reason") == "length"' in src
    assert S.MAX_OUTPUT_TOKENS >= 2000, "too tight: reasoning tokens share this budget"


test_truncation_guard_exists()
test_persona_queries()
test_tier_monotonicity()
test_resume()
assert "n=" in paired_test([], "A", "C")
print(f"ok -- {len(RECS)} scenarios: staleness/missing/vendor guards fire, "
      f"resume regenerates only what changed, tiers stay monotonic (A subset B subset C)")
