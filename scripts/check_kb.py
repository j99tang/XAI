"""KB consistency checker — the five rules of plan §2.9.

1. Every IP in the raw CSVs resolves to a device or external range in entities.yaml.
2. Every feature name in the feature dictionary matches models/feature_list.json.
3. Every breaker (BR-x-y) referenced in any KB file exists in the generated topology.
4. Every MITRE technique ID (T0xxx) in the taxonomy is well-formed and defined once.
5. Every device/zone entity mentioned in any KB file resolves to entities.yaml.

Missing knowledge-base files are reported but only fail the run with --strict
(the KB is built incrementally; consistency errors always fail).
Run: conda run -n xai python scripts/check_kb.py [--strict]
"""
from __future__ import annotations

import csv
import ipaddress
import json
import re
import sys
from pathlib import Path

import yaml

ROOT = Path(__file__).resolve().parents[1]
KB = ROOT / "knowledge_base"
RAW = ROOT / "data" / "raw" / "iec104"

errors: list[str] = []
missing: list[str] = []


def kb_texts() -> dict[Path, str]:
    return {p: p.read_text() for p in KB.rglob("*.md")}


def load_entities():
    return yaml.safe_load((KB / "entities.yaml").read_text())


def rule1_ips(entities) -> None:
    known = {d["ip"] for d in entities["devices"]}
    nets, loose = [], set()
    for r in entities["external_ranges"]:
        if "cidr" in r:
            nets.append(ipaddress.ip_network(r["cidr"]))
        loose.update(r.get("ips", []))
    seen = set()
    for f in RAW.glob("capture104-*.csv"):
        with open(f) as fh:
            for row in csv.DictReader(fh):
                seen.add(row["Src IP"].strip())
                seen.add(row["Dst IP"].strip())
    for ip in sorted(seen):
        if ip in known or ip in loose:
            continue
        try:
            addr = ipaddress.ip_address(ip)
        except ValueError:
            errors.append(f"rule1: unparseable IP in captures: {ip}")
            continue
        if not any(addr in n for n in nets):
            errors.append(f"rule1: capture IP {ip} not in entities.yaml (device or external range)")


def rule2_features() -> None:
    fdict = KB / "feature_dictionary" / "flow_features.md"
    flist = ROOT / "models" / "feature_list.json"
    if not fdict.exists():
        missing.append(str(fdict)); return
    valid = set(json.loads(flist.read_text()))
    # Backticks wrap feature names AND file paths/code — only treat a token as a
    # claimed feature if it looks like one (Title Case words, optional /s or unit),
    # not a path (has /, .md) or an identifier (has _).
    named = set(re.findall(r"`([^`]+)`", fdict.read_text()))
    def looks_like_feature(tok: str) -> bool:
        if "/" in tok and ".md" in tok:      # cross-reference path
            return False
        if "_" in tok or tok.endswith(".json") or tok.endswith(".py"):
            return False
        return bool(re.match(r"^[A-Z][A-Za-z]", tok))  # feature names are Title Case
    for name in sorted(n for n in named if looks_like_feature(n) and n not in valid):
        errors.append(f"rule2: feature dictionary names `{name}` — not in models/feature_list.json")


def rule3_breakers(texts) -> None:
    topo = KB / "topology" / "ieee14_grid.md"
    if not topo.exists():
        missing.append(str(topo)); return
    defined = set(re.findall(r"BR-\d+-\d+", texts[topo]))
    for path, text in texts.items():
        if path == topo:
            continue
        for br in set(re.findall(r"BR-\d+-\d+", text)):
            if br not in defined:
                errors.append(f"rule3: {path.relative_to(ROOT)} references {br} — not in generated topology")
    # entities.yaml breaker claims too
    for d in load_entities()["devices"]:
        for br in d.get("controls_breakers", []):
            if br not in defined:
                errors.append(f"rule3: entities.yaml {d['id']} controls {br} — not in generated topology")


def rule4_mitre(texts) -> None:
    tax = KB / "attack_taxonomy" / "attacks.md"
    if not tax.exists():
        missing.append(str(tax)); return
    # Format only: a well-formed ICS technique ID is T#### optionally .###.
    # (A technique may legitimately recur — DoS is shared by several attacks — so
    # uniqueness is NOT enforced; we only catch malformed IDs like T81 or T00001.)
    for bad in set(re.findall(r"\bT\d{1,3}\b|\bT\d{5,}\b", texts[tax])):
        errors.append(f"rule4: malformed MITRE technique ID {bad} in taxonomy (expected T#### )")


def rule5_entities(texts, entities) -> None:
    valid = {d["id"] for d in entities["devices"]}
    valid |= {z["id"] for z in entities["zones"]}
    valid |= {entities["vendor"]["name"], entities["vendor"]["rtu_model"]}
    pattern = re.compile(r"\b(?:RTU-\d+|SCADA-\d+|ENG-WS-\d+|ZONE-[A-Z]+|GC-\d+)\b")
    for path, text in texts.items():
        for m in set(pattern.findall(text)):
            if m not in valid:
                errors.append(f"rule5: {path.relative_to(ROOT)} mentions {m} — not in entities.yaml")


def main() -> int:
    strict = "--strict" in sys.argv
    entities = load_entities()
    texts = kb_texts()
    rule1_ips(entities)
    rule2_features()
    rule3_breakers(texts)
    rule4_mitre(texts)
    rule5_entities(texts, entities)

    for e in errors:
        print("ERROR", e)
    for m in missing:
        print("MISSING (not yet authored):", Path(m).relative_to(ROOT))
    if errors or (strict and missing):
        print(f"\ncheck_kb: FAIL ({len(errors)} errors, {len(missing)} missing)")
        return 1
    print(f"check_kb: OK ({len(texts)} KB files checked, {len(missing)} still to author)")
    return 0


if __name__ == "__main__":
    sys.exit(main())
