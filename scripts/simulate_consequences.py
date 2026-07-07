"""Physical-consequence simulator (plan §2.9 / Phase 4.4) — the domain "expert".

Given an attack that disables a device or opens breakers, compute the physical
consequence on IEEE 14-bus with pandapower: open the corresponding branch(es),
re-run power flow, report overloads / voltage violations — or islanding if the
network no longer solves. This is the machine-derived ground truth the CPAS
C-dimension scores against; nothing here is hand-authored.

Breaker naming: `BR-<from>-<to>` (1-based bus numbers) maps to the line OR
transformer between those buses (see scripts/export_topology.py).

Usage:
  conda run -n xai python scripts/simulate_consequences.py --selfcheck
  conda run -n xai python scripts/simulate_consequences.py --device RTU-3
  conda run -n xai python scripts/simulate_consequences.py --breaker BR-4-9
  conda run -n xai python scripts/simulate_consequences.py --all      # every RTU -> JSON files
"""
from __future__ import annotations

import argparse
import json
from pathlib import Path

import pandapower as pp
import pandapower.networks as pn
import yaml

ROOT = Path(__file__).resolve().parents[1]
OUT_DIR = ROOT / "experiments" / "scenarios"
ENTITIES = ROOT / "knowledge_base" / "entities.yaml"

V_MIN, V_MAX = 0.94, 1.10        # p.u., matches topology doc
LOAD_ALARM, LOAD_VIOL = 90.0, 100.0  # % of branch rating


def branch_map(net) -> dict[frozenset[int], list[tuple[str, int]]]:
    """(bus_a, bus_b) [1-based] -> list of ('line'|'trafo', index)."""
    m: dict[frozenset[int], list[tuple[str, int]]] = {}
    for i, r in net.line.iterrows():
        m.setdefault(frozenset({int(r.from_bus) + 1, int(r.to_bus) + 1}), []).append(("line", i))
    for i, r in net.trafo.iterrows():
        m.setdefault(frozenset({int(r.hv_bus) + 1, int(r.lv_bus) + 1}), []).append(("trafo", i))
    return m


def open_breaker(net, bmap, breaker: str) -> list[str]:
    """Take the branch(es) named by a breaker out of service. Returns what it opened."""
    a, b = (int(x) for x in breaker.replace("BR-", "").split("-"))
    key = frozenset({a, b})
    if key not in bmap:
        raise ValueError(f"{breaker}: no case14 branch between buses {a} and {b}")
    opened = []
    for kind, idx in bmap[key]:
        getattr(net, kind).at[idx, "in_service"] = False
        opened.append(f"{kind} {idx}")
    return opened


def violations(net) -> dict:
    v = {"voltage": [], "overload": []}
    for bus, vm in net.res_bus.vm_pu.items():
        if vm < V_MIN or vm > V_MAX:
            v["voltage"].append({"bus": int(bus) + 1, "vm_pu": round(float(vm), 3)})
    for tbl in ("res_line", "res_trafo"):
        res = getattr(net, tbl)
        for idx, load in res.loading_percent.items():
            if load >= LOAD_ALARM:
                v["overload"].append({"branch": f"{tbl.replace('res_', '')} {idx}",
                                      "loading_percent": round(float(load), 1),
                                      "violation": bool(load >= LOAD_VIOL)})
    return v


def simulate(breakers: list[str]) -> dict:
    """Open the given breakers on a fresh case14, solve, classify the consequence."""
    net = pn.case14()
    bmap = branch_map(net)
    opened = []
    for br in breakers:
        opened += open_breaker(net, bmap, br)
    try:
        pp.runpp(net)
    except pp.LoadflowNotConverged:
        return {"breakers": breakers, "opened_branches": opened,
                "converged": False,
                "consequence": "islanding / loss of supply — network does not solve with these "
                               "branches open (a bus or group is de-energized)"}
    v = violations(net)
    physical = bool(v["voltage"]) or any(o["violation"] for o in v["overload"])
    return {"breakers": breakers, "opened_branches": opened, "converged": True,
            "violations": v,
            "consequence": ("physical: " + _describe(v)) if physical
            else "no physical violation — consequence is loss of visibility/control only "
                 "(grid absorbs the outage via redistribution; base-case headroom is large)"}


def _describe(v: dict) -> str:
    parts = []
    if v["overload"]:
        parts.append("overloads: " + ", ".join(f"{o['branch']} @ {o['loading_percent']}%"
                                                for o in v["overload"] if o["violation"]))
    if v["voltage"]:
        parts.append("voltage: " + ", ".join(f"bus {x['bus']} @ {x['vm_pu']}pu" for x in v["voltage"]))
    return "; ".join(parts)


def devices() -> dict[str, dict]:
    ents = yaml.safe_load(ENTITIES.read_text())
    return {d["id"]: d for d in ents["devices"]}


def selfcheck() -> int:
    """Acceptance check: base case (no outage) converges with no violations."""
    res = simulate([])
    ok = res["converged"] and not res["violations"]["voltage"] and \
        not any(o["violation"] for o in res["violations"]["overload"])
    print("baseline:", "OK — converges, no violations" if ok else f"FAIL — {res}")
    return 0 if ok else 1


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--device", help="entities.yaml device id, e.g. RTU-3 (opens all its breakers)")
    ap.add_argument("--breaker", help="single breaker, e.g. BR-4-9")
    ap.add_argument("--all", action="store_true", help="simulate every RTU -> JSON files")
    ap.add_argument("--selfcheck", action="store_true")
    a = ap.parse_args()

    if a.selfcheck:
        return selfcheck()

    OUT_DIR.mkdir(parents=True, exist_ok=True)
    if a.all:
        for did, d in devices().items():
            if not d.get("controls_breakers"):
                continue
            res = simulate(d["controls_breakers"]) | {"device": did, "ip": d["ip"], "bus": d["bus"]}
            (OUT_DIR / f"consequences_{did}.json").write_text(json.dumps(res, indent=2))
            print(f"{did}: {res['consequence'][:80]}")
        return 0

    if a.device:
        d = devices()[a.device]
        res = simulate(d["controls_breakers"]) | {"device": a.device, "ip": d["ip"], "bus": d["bus"]}
    elif a.breaker:
        res = simulate([a.breaker])
    else:
        ap.error("give one of --selfcheck / --device / --breaker / --all")
    print(json.dumps(res, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
