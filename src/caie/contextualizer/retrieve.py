"""Phase 3.2: AnomalyEvent -> per-persona Multi-Domain Context Blocks (plan §11.1).

Uses only_need_context so no generation happens here; synthesis is a separate step.

WHY PER-PERSONA (D42). The original design retrieved ONCE with a persona-agnostic
query and reused the block for all three personas — the proposal's efficiency claim.
Measurement killed it: one ranking cannot serve three different information needs.
The shared query asks about device / attack / consequence / "required response" and
never mentions reporting, so the compliance chunk ranked LAST of 7 and sat at char
26,531 of a 28,672-char block. Every workable `max_chars` cut it, and the CIP rule
reached the synthesizer in **0 of 30 scenarios** — while 27/30 regulator narratives
asserted a "24 hours" figure found nowhere in the KB.

Raising the cap does not fix it: at 30k the 8B collapses completely, emitting
byte-identical text across scenarios AND personas (incident-specific content is ~1.7%
of that input). So the two requirements — include the compliance rule, preserve persona
conditioning — are arithmetically incompatible under one shared, positionally-truncated
block.

Each persona now issues its own query, so what it needs ranks HIGH and survives in a
SMALL block. Cost, stated openly: three retrievals per alert instead of one. The
"retrieve once, reuse 3x" efficiency claim is forfeited — it was only ever valid if one
block adequately served all three personas, which it demonstrably did not.
"""
from __future__ import annotations

import ipaddress

import yaml
from lightrag import QueryParam

from caie.contextualizer.rag import KB_DIR
from caie.schemas.anomaly_event import AnomalyEvent

_ENTITIES = None


def resolve_device(ip: str) -> str:
    """Deterministic IP→device lookup from entities.yaml (the authoritative join
    key — a table join, NOT a semantic search). Returns an authoritative fact
    block, so the synthesizer never has to invent device/bus/breaker names."""
    global _ENTITIES
    if _ENTITIES is None:
        _ENTITIES = yaml.safe_load((KB_DIR / "entities.yaml").read_text())
    for d in _ENTITIES["devices"]:
        if d["ip"] == ip:
            loc = f", at Bus {d['bus']}" if d["bus"] else ""
            brk = (", controls breakers " + ", ".join(d["controls_breakers"])) if d["controls_breakers"] else ""
            # cip_class is load-bearing for the regulator persona (D47): CIP-008-6 only
            # triggers for a BES Cyber System or an associated EACMS/PACS, so without the
            # device's classification the reportability question is unanswerable by any
            # model that honours the personas' "use ONLY facts in the provided context"
            # rule. gpt-5.5 correctly withheld on exactly this ground. It is a property of
            # the asset, like zone and bus — not the answer to R, which still requires
            # deciding attempt vs compromise and applying the clock.
            cip = f", {d['cip_class']} under NERC CIP (authored overlay)" if d.get("cip_class") else ""
            return (f"DEVICE (authoritative, from IP map): {ip} = {d['id']}, {d['role']}, "
                    f"zone {d['zone']}{loc}{brk}{cip}.")
    for r in _ENTITIES["external_ranges"]:
        if "cidr" in r and ipaddress.ip_address(ip) in ipaddress.ip_network(r["cidr"]):
            return f"DEVICE (authoritative): {ip} is not a grid asset — {r['label']}."
        if ip in r.get("ips", []):
            return f"DEVICE (authoritative): {ip} is not a grid asset — {r['label']}."
    return f"DEVICE (authoritative): {ip} is not in the IP→device map."


def evidence_block(ev: AnomalyEvent) -> str:
    """The NETWORK-side evidence: what the IDS predicted and what SHAP attributed it to.

    Shared by tier B and by the tier-C context block so that **tier C is literally a
    SUPERSET of tier B** (C = B + retrieved context). Before this existed, the features
    were used to build the retrieval query but never handed to the synthesizer, so tier C
    had LESS evidence than tier B — the data-scientist persona was asked which features
    drove the prediction and was never told, and duly invented them ("Total Bwd packets,
    SHAP 0.35" against a real top feature of Bwd IAT Min at +0.068). One formatter, used
    by both tiers, keeps the ablation monotonic by construction rather than by care.
    """
    feats = "\n".join(f"  {f.name}: value={f.value:g}, SHAP={f.shap:+.3f}"
                      for f in ev.top_features)
    return (f"INTRUSION ALERT\nprediction: {ev.prediction}\n"
            f"confidence: {ev.confidence:.2f}\ndestination: {ev.dst_ip}:{ev.dst_port}\n"
            f"top SHAP features (toward 'attack'):\n{feats}")


# What each persona needs the graph to surface. These are RETRIEVAL intents, not
# grading criteria and not answers — they steer ranking toward the KB region that role
# depends on. Kept deliberately close to the persona's own deliverable
# (configs/personas/*.md) so retrieval and generation are asking for the same thing.
PERSONA_INTENT = {
    "operator": ("What is the operator response playbook for this device: which breakers "
                 "and RTUs to check, whether to switch to manual control, isolation and "
                 "switching steps, and the physical risk to the grid?"),
    "data_scientist": ("What do these network flow features mean, what attack pattern does "
                       "this feature signature indicate, and what can flow statistics prove "
                       "or not prove about protocol-level behaviour?"),
    "regulator": ("Is this a Reportable Cyber Security Incident under NERC CIP-008-6? What "
                  "is the reporting timeline — one hour for an incident versus end of the "
                  "next calendar day for an attempt — and who must be notified (E-ISAC, "
                  "NCCIC)? Which NIST CSF function does the response sit under?"),
}


def event_to_query(ev: AnomalyEvent, persona: str | None = None) -> str:
    """The retrieval query: SHAP features (network evidence) + destination IP (the join
    key to device/grid), plus the persona's information need when one is given.

    `persona=None` reproduces the original shared query. Retained for the D42 comparison
    and for any analysis that needs the pre-§11.1 behaviour; the pipeline always passes a
    persona."""
    feats = ", ".join(f"{f.name} (SHAP {f.shap:+.2f}, value {f.value:g})"
                      for f in ev.top_features)
    base = (
        f"An IDS flagged a network flow to {ev.dst_ip} on port {ev.dst_port} as "
        f"'{ev.prediction}' with confidence {ev.confidence:.2f}. The most influential "
        f"flow features were: {feats}. "
    )
    if persona is None:
        return base + (f"What device is {ev.dst_ip}, what attack does this feature pattern "
                       f"indicate, and what is the physical consequence and required response?")
    return base + f"What device is {ev.dst_ip}? " + PERSONA_INTENT[persona]


async def retrieve_context(rag, ev: AnomalyEvent, persona: str, mode: str = "hybrid",
                           top_k: int = 8, max_chars: int = 9000) -> str:
    """One persona's context block: device join + network evidence + retrieved KB prose.

    `max_chars` stays as a SAFETY RAIL, not as the content selector it had become. With a
    persona-targeted query the needed material ranks high, so the cap should rarely bind;
    if it does, what it trims is genuinely lower-ranked for THIS role. 9,000 chars is the
    only value measured not to collapse the 8B (D42) — every larger value tested produced
    byte-identical output across scenarios and personas.

    `top_k` is 8 rather than 12: with three targeted queries each block should be focused,
    and fewer, better-ranked chunks beat more diluted ones. This is the principled size
    knob — relevance-ranked — as opposed to the positional character cut.
    """
    param = QueryParam(mode=mode, only_need_context=True, top_k=top_k, chunk_top_k=top_k)
    rag_block = await rag.aquery(event_to_query(ev, persona), param=param) or ""
    # Order matters: authoritative device join, then the network evidence, then retrieved
    # KB prose. The cap applies to the RETRIEVED tail only, so neither the device chain
    # nor the SHAP evidence can ever be trimmed away.
    return f"{resolve_device(ev.dst_ip)}\n\n{evidence_block(ev)}\n\n{rag_block[:max_chars]}"


async def retrieve_all(rag, ev: AnomalyEvent, personas) -> dict[str, str]:
    """One context block per persona. Three retrievals per alert — the cost of §11.1."""
    return {p: await retrieve_context(rag, ev, p) for p in personas}
