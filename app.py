"""CAIE demo — watch an IDS alert become a role-specific explanation, live.

The three tiers of the ablation, computed on demand rather than looked up:

  TIER A  RandomForest prediction + confidence          (what an operator gets today)
  TIER B  + SHAP attributions over the flow features    (XAI, but ungrounded)
  TIER C  + graph-retrieved context, per persona        (the full system)

Run:  conda run -n xai streamlit run app.py

Honest note about the paste box: a tier-A alert is four lines and does NOT contain the
79 flow features SHAP needs, so a pasted alert is RESOLVED to its underlying flow rather
than analysed directly. The app says so on screen — a demo that quietly implied otherwise
would be misrepresenting what the pipeline does.
"""
from __future__ import annotations

import asyncio, json, re, sys, time
from pathlib import Path

import joblib
import streamlit as st

ROOT = Path(__file__).resolve().parent
sys.path.insert(0, str(ROOT / "src"))

from caie.contextualizer.retrieve import evidence_block, resolve_device   # noqa: E402
from caie.schemas.anomaly_event import AnomalyEvent                       # noqa: E402
from caie.xai.explain import top_attributions                             # noqa: E402

SCEN = ROOT / "experiments" / "scenarios"
PERSONAS = ["operator", "data_scientist", "regulator"]
MODELS = {                       # label -> (backend, model id)
    "gpt-5.5  (ceiling)":            ("openai", "openai/gpt-5.5"),
    "qwen3-235b  (open, large)":     ("openai", "qwen/qwen3-235b-a22b-2507"),
    "llama-3.3-70b  (open)":         ("openai", "meta-llama/llama-3.3-70b-instruct"),
    "qwen3-32b  (open)":             ("openai", "qwen/qwen3-32b"),
    "llama3.1:8b  (LOCAL, offline)": ("ollama", "llama3.1:8b"),
}

st.set_page_config(page_title="CAIE demo", page_icon="⚡", layout="wide")


@st.cache_resource(show_spinner="loading IDS model…")
def load_model():
    m = joblib.load(ROOT / "models" / "ids_rf.joblib")
    feats = json.loads((ROOT / "models" / "feature_list.json").read_text())
    return m, feats


@st.cache_resource(show_spinner="loading knowledge graph…")
def load_rag():
    from caie.contextualizer.rag import build_rag
    return asyncio.run(build_rag())


@st.cache_data(show_spinner="loading scenarios…")
def load_scenarios():
    return [json.loads(p.read_text()) for p in sorted(SCEN.glob("scenario_*.json"))]


@st.cache_resource(show_spinner="loading capture (320k flows)…")
def load_test_split():
    from caie.ids.dataset import load_raw, split
    df = load_raw()
    X_tr, X_te, y_tr, y_te, m_tr, m_te = split(df)
    return X_te, m_te, df.loc[X_te.index, "Label"]


@st.cache_data(show_spinner=False)
def devices():
    import yaml
    d = yaml.safe_load((ROOT / "knowledge_base" / "entities.yaml").read_text())
    return {x["id"]: x for x in d["devices"]}


def event_from_flow(row, model, feats, dst_id: str, k: int = 5) -> AnomalyEvent:
    """Run the REAL pipeline on a flow record: RandomForest -> SHAP -> AnomalyEvent.

    `dst_id` is the authored target device. It has to be chosen rather than read from the
    flow because of the data reality this project is built around (decision log D24): no
    attack flow in the SANDI-2024 capture targets a real RTU — attack traffic lives on the
    121.x testbed subnet, only benign traffic reaches 10.0.0.x. So a genuine attack flow
    yields working tiers A and B and a DEAD tier C, since the device join correctly
    reports no grid asset at 121.x. Pairing real flow statistics with an authored target
    is exactly what `scripts/make_fact_sheets.py` does to build the scenarios.
    """
    d = devices()[dst_id]
    proba = float(model.predict_proba(row[feats].to_frame().T.astype(float))[0, 1])
    return AnomalyEvent(
        flow_id=str(row.name), src_ip="121.142.26.78", dst_ip=d["ip"], dst_port=2404,
        prediction="attack" if proba >= 0.5 else "normal", confidence=proba,
        top_features=top_attributions(model, feats, row, k))


def tier_a(ev: AnomalyEvent) -> str:
    return (f"INTRUSION ALERT\nprediction: {ev.prediction}\n"
            f"confidence: {ev.confidence:.2f}\ndestination: {ev.dst_ip}:{ev.dst_port}")


def parse_alert(text: str, scenarios) -> list[dict]:
    """Resolve a pasted tier-A alert to the flows it could be. Returns ALL equally-good
    matches, not the first.

    A tier-A alert carries destination, prediction and confidence — and that is often not
    enough to identify the incident: several scenarios hit the same RTU at confidence 1.00.
    Silently picking one would hide the very thing this demo exists to show, namely how
    little an unenriched alert actually tells you.
    """
    ip = re.search(r"destination:\s*([\d.]+)(?::(\d+))?", text)
    conf = re.search(r"confidence:\s*([\d.]+)", text)
    if not ip:
        return []
    cands = [s for s in scenarios if s["anomaly_event"]["dst_ip"] == ip.group(1)]
    if cands and conf:
        target = float(conf.group(1))
        best = min(abs(s["anomaly_event"]["confidence"] - target) for s in cands)
        cands = [s for s in cands
                 if abs(s["anomaly_event"]["confidence"] - target) == best]
    return cands


# ---------------------------------------------------------------- sidebar
st.sidebar.title("⚡ CAIE")
st.sidebar.caption("Context-Aware Intrusion Explanation")
label = st.sidebar.selectbox("Synthesizer", list(MODELS), index=0)
backend, model_id = MODELS[label]
if backend == "ollama":
    st.sidebar.info("Fully offline — nothing leaves this machine. Slower (~30 s/persona).")
else:
    st.sidebar.caption("via OpenRouter · ~5 s/persona · ~$0.02 per run")
show_ctx = st.sidebar.checkbox("show retrieved context", value=False)
show_gold = st.sidebar.checkbox("show gold facts (answer key)", value=False)

scenarios = load_scenarios()

# ---------------------------------------------------------------- input
st.title("From alert to explanation")
st.caption("The same incident at three levels of grounding. Tiers A and B are computed "
           "from the model; tier C adds retrieved context and role conditioning.")

tab_pick, tab_flow, tab_search, tab_paste = st.tabs(
    ["Pick a scenario", "Paste a flow record", "Search the capture", "Resolve an alert"])
rec, ev = None, None

with tab_pick:
    labels = [f"{s['scenario_id']}  ·  {s['gold_facts']['attack_class']}  ·  "
              f"{s['kind']}  ·  {s.get('consequence_class','n/a')}" for s in scenarios]
    rec = scenarios[st.selectbox("incident", range(len(scenarios)),
                                 format_func=lambda i: labels[i], label_visibility="collapsed")]
    ev = AnomalyEvent.from_dict(rec["anomaly_event"])

with tab_flow:
    st.caption("Paste a flow record — 78 comma-separated values, or a CSV row from the "
               "capture. The IDS and SHAP run on it for real; nothing is looked up.")
    model, feats = load_model()
    raw = st.text_area("flow", height=110, label_visibility="collapsed",
                       placeholder=", ".join(feats[:6]) + ", …  (78 values)")
    tgt = st.selectbox("target device (authored overlay — see note below)",
                       [d for d in devices() if devices()[d].get("bus")], key="flow_tgt")
    if raw.strip():
        vals = [v.strip() for v in re.split(r"[,\s]+", raw.strip()) if v.strip()]
        if len(vals) != len(feats):
            st.error(f"Expected {len(feats)} values, got {len(vals)}. "
                     f"Order must match `models/feature_list.json`.")
        else:
            try:
                import pandas as pd
                row = pd.Series([float(v) for v in vals], index=feats, name="pasted")
                ev = event_from_flow(row, model, feats, tgt); rec = None
                st.success(f"IDS + SHAP computed on your input → target {tgt}", icon="✅")
            except ValueError as e:
                st.error(f"Could not parse as numbers: {e}")

with tab_search:
    st.caption("Pick a real captured flow. Tiers A and B are computed on it live.")
    X_te, m_te, labels_te = load_test_split()
    c1, c2, c3 = st.columns([2, 1, 1])
    lab = c1.selectbox("attack class", sorted(labels_te.unique()), key="s_lab")
    tgt2 = c2.selectbox("target device", [d for d in devices() if devices()[d].get("bus")], key="s_tgt")
    pool = X_te.index[(labels_te == lab).values]
    n = c3.number_input(f"row (of {len(pool):,})", 0, max(len(pool) - 1, 0), 0, key="s_n")
    if st.button("Analyse this flow", key="s_go"):
        model, feats = load_model()
        idx = pool[int(n)]
        st.session_state["searched"] = (idx, tgt2)
    if "searched" in st.session_state:
        idx, t = st.session_state["searched"]
        model, feats = load_model()
        ev = event_from_flow(X_te.loc[idx], model, feats, t); rec = None
        st.success(f"flow `{m_te.loc[idx,'Flow ID']}` · true label **{labels_te.loc[idx]}** "
                   f"· real dst `{m_te.loc[idx,'Dst IP']}` → analysed against **{t}**", icon="✅")
        st.caption("The real destination is the testbed attack subnet; no capture flow targets "
                   "an RTU (D24), so the physical target is the authored overlay.")

with tab_paste:
    st.caption("Resolve a tier-A alert back to a known incident. Its real value is showing "
               "how little an alert identifies.")
    txt = st.text_area("alert", height=110, label_visibility="collapsed",
                       placeholder="INTRUSION ALERT\nprediction: attack\nconfidence: 1.00\n"
                                   "destination: 10.0.0.1:2404")
    if txt.strip():
        hits = parse_alert(txt, scenarios)
        if not hits:
            st.error("No known flow matches that destination.")
        else:
            if len(hits) > 1:
                st.warning(f"**This alert matches {len(hits)} different incidents.** Destination "
                           f"and confidence do not identify which one — that is how little a "
                           f"tier-A alert carries.", icon="⚠️")
                rec = hits[st.radio("which incident?", range(len(hits)), horizontal=True,
                                    format_func=lambda i: f"{hits[i]['scenario_id']} · "
                                                          f"{hits[i]['gold_facts']['attack_class']}")]
            else:
                rec = hits[0]
                st.info(f"Resolved to **{rec['scenario_id']}**.", icon="✅")
            ev = AnomalyEvent.from_dict(rec["anomaly_event"])
            st.caption("A tier-A alert carries no flow features, so SHAP is recovered from the "
                       "underlying record — it cannot be computed from the pasted text.")

if ev is None:
    st.stop()

go = st.button("Explain this incident", type="primary", use_container_width=True)

# ---------------------------------------------------------------- tiers A & B
c1, c2 = st.columns(2)
with c1:
    st.subheader("Tier A · IDS alone")
    st.caption("What a control room gets today")
    st.code(tier_a(ev), language=None)
with c2:
    st.subheader("Tier B · + SHAP")
    st.caption("XAI, but nothing physical to attach it to")
    st.code(evidence_block(ev), language=None)

if show_gold and rec is not None:
    with st.expander("gold facts (the judge's answer key)"):
        st.json(rec["gold_facts"])
elif show_gold:
    st.caption("No gold facts — this flow was analysed live, not drawn from the scenario set.")

# ---------------------------------------------------------------- tier C
st.subheader("Tier C · + retrieved context, per role")
st.caption(f"synthesizer: `{model_id}`")

if go:
    import os
    os.environ["CAIE_SYNTH_BACKEND"], os.environ["CAIE_SYNTH_MODEL"] = backend, model_id
    for m in [k for k in sys.modules if k.startswith("caie.contextualizer.synthesize")]:
        del sys.modules[m]                      # re-read the env vars on switch
    from caie.contextualizer.retrieve import retrieve_context
    from caie.contextualizer.synthesize import synthesize_one

    rag = load_rag()
    cols = st.columns(3)
    t0 = time.time()
    for col, persona in zip(cols, PERSONAS):
        with col:
            st.markdown(f"**{persona.replace('_',' ')}**")
            with st.spinner("retrieving + writing…"):
                ctx = asyncio.run(retrieve_context(rag, ev, persona))
                try:
                    out = synthesize_one(ctx, persona)
                except Exception as e:
                    st.error(f"{type(e).__name__}: {e}"); continue
            st.markdown(out)
            if show_ctx:
                with st.expander(f"context given to the model ({len(ctx):,} chars)"):
                    st.text(ctx)
    st.success(f"three role-specific explanations in {time.time()-t0:.1f}s")
else:
    st.info("Press **Explain this incident** to run retrieval and synthesis live.")
