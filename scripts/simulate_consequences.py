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
import collections
import itertools
import json
from functools import lru_cache
from pathlib import Path

import numpy as np
import pandapower as pp
import pandapower.networks as pn
import yaml

ROOT = Path(__file__).resolve().parents[1]
OUT_DIR = ROOT / "experiments" / "scenarios"
ENTITIES = ROOT / "knowledge_base" / "entities.yaml"

V_MIN, V_MAX = 0.94, 1.10        # p.u., matches topology doc
LOAD_ALARM, LOAD_VIOL = 90.0, 100.0  # % of branch rating

# --- Thermal ratings (D36) -------------------------------------------------
# pandapower's case14 inherits MATPOWER's rateA = 0 ("unlimited"), which it renders
# as max_i_ka = 42.3 on every line. Against that, 2x load with no outage loads a line
# to 3.7% -- so LOAD_VIOL = 100 was unreachable and the overload branch below was dead
# code. Since plan §1 justifies IEEE-14 precisely because cascading/thermal overload is
# a transmission phenomenon, unrateable branches make the C dimension untestable.
#
# We rate lines on the standard planning criterion instead of an arbitrary number:
# a line's rating is the worst current it carries across every SINGLE-branch outage
# (N-1), times a margin. The system is then N-1 secure by construction -- any one
# breaker may open with no thermal violation -- while N-2 and deeper bite. That is a
# citable criterion, not a tuned constant, and `selfcheck()` asserts it holds.
#
# margin is the calibration knob. 1.25 puts N-0 at ~60% of rating (realistic for
# transmission) and yields a usable spread over the 76 breaker subsets x 4 load levels:
#   margin  ABSORBED  OVERLOAD  OVER+VOLT  ISLAND   N-0 max
#     1.00        39       202         35      28      75%
#     1.25       107       134         35      28      60%   <- chosen
#     1.40       138       103         35      28      53%
# Pure voltage-only violations do not occur under N-1 ratings on this network: when
# voltage collapses, branches are already overloaded. That is physical, not a gap.
N1_MARGIN = 1.25

# NOTE: rate LINES only. A transformer's sn_mva participates in pandapower's impedance
# model (vk_percent is relative to it), so scaling it changes the power flow itself,
# not just the limit -- it breaks base-case convergence. Verified the hard way.


@lru_cache(maxsize=1)
def n1_line_ratings(margin: float = N1_MARGIN) -> tuple[float, ...]:
    """max_i_ka per line = worst current under any single-branch outage, x margin.
    ~20 power flows; cached because every simulate() call needs it."""
    base = pn.case14()
    pp.runpp(base)
    worst = base.res_line.i_ka.values.copy()
    for tbl in ("line", "trafo"):
        for idx in range(len(getattr(base, tbl))):
            net = pn.case14()
            getattr(net, tbl).at[idx, "in_service"] = False
            try:
                pp.runpp(net)
            except pp.LoadflowNotConverged:
                continue  # this outage islands the grid; no thermal info to add
            worst = np.maximum(worst, np.nan_to_num(net.res_line.i_ka.values))
    return tuple(worst * margin)


def rated_case14(load_scale: float = 1.0):
    """A fresh case14 with real thermal ratings, optionally stressed."""
    net = pn.case14()
    net.line["max_i_ka"] = list(n1_line_ratings())
    if load_scale != 1.0:
        net.load.p_mw *= load_scale
        net.load.q_mvar *= load_scale
    return net


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


def simulate(breakers: list[str], load_scale: float = 1.0) -> dict:
    """Open the given breakers on a fresh, thermally-rated case14, solve, classify."""
    net = rated_case14(load_scale)
    bmap = branch_map(net)
    opened = []
    for br in breakers:
        opened += open_breaker(net, bmap, br)
    try:
        pp.runpp(net)
    except pp.LoadflowNotConverged:
        return {"breakers": breakers, "opened_branches": opened,
                "load_scale": load_scale, "converged": False,
                "consequence": "islanding / loss of supply — network does not solve with these "
                               "branches open (a bus or group is de-energized)"}
    v = violations(net)
    physical = bool(v["voltage"]) or any(o["violation"] for o in v["overload"])
    return {"breakers": breakers, "opened_branches": opened,
            "load_scale": load_scale, "converged": True, "violations": v,
            "consequence": ("physical: " + _describe(v)) if physical
            else "no physical violation — consequence is loss of visibility/control only "
                 "(the grid absorbs the outage; remaining branches stay within thermal "
                 "rating and all bus voltages stay in band)"}


def _describe(v: dict) -> str:
    parts = []
    if v["overload"]:
        parts.append("overloads: " + ", ".join(f"{o['branch']} @ {o['loading_percent']}%"
                                                for o in v["overload"] if o["violation"]))
    if v["voltage"]:
        parts.append("voltage: " + ", ".join(f"bus {x['bus']} @ {x['vm_pu']}pu" for x in v["voltage"]))
    return "; ".join(parts)


def classify(res: dict) -> str:
    """One label per consequence, for stratifying the scenario set (D35)."""
    if not res["converged"]:
        return "ISLAND"
    over = any(o["violation"] for o in res["violations"]["overload"])
    volt = bool(res["violations"]["voltage"])
    return "OVER+VOLT" if over and volt else "OVERLOAD" if over else "VOLTAGE" if volt else "ABSORBED"


LOAD_LEVELS = (1.0, 1.1, 1.25, 1.5)


def build_library() -> list[dict]:
    """Every breaker SUBSET of every RTU x every load level (D35).

    The old `--all` simulated only each device's FULL breaker set at base load, so
    consequence was a pure function of device identity: 4 devices -> 4 consequences,
    and scenarios sharing a device were identical on the C, A and R dimensions.
    Enumerating subsets is what decouples consequence from device — a partial
    compromise (an attacker opens one line, not four) is also the more realistic
    threat model.
    """
    lib = []
    for did, d in devices().items():
        brs = d.get("controls_breakers") or []
        for r in range(1, len(brs) + 1):
            for combo in itertools.combinations(brs, r):
                for scale in LOAD_LEVELS:
                    res = simulate(list(combo), scale)
                    lib.append({"device": did, "ip": d["ip"], "bus": d["bus"],
                                "n_breakers": r, "class": classify(res), **res})
    return lib


def devices() -> dict[str, dict]:
    ents = yaml.safe_load(ENTITIES.read_text())
    return {d["id"]: d for d in ents["devices"]}


def _clean(res: dict) -> bool:
    return (res["converged"] and not res["violations"]["voltage"]
            and not any(o["violation"] for o in res["violations"]["overload"]))


def selfcheck() -> int:
    """Acceptance checks for the rating basis (D36).

    1. N-0: base case converges with no violations.
    2. N-1 security: NO single breaker opening violates a thermal limit — this is the
       criterion the ratings are derived from, so it must hold by construction.
    3. The overload path is REACHABLE: some deeper outage must actually violate.
       Guards against silently regressing to unlimited ratings, where the whole
       overload branch is dead code and the C dimension cannot be tested.
    """
    fails = []
    if not _clean(simulate([])):
        fails.append("N-0 base case is not clean")

    singles = sorted({b for d in devices().values() for b in d.get("controls_breakers", [])})
    bad = [b for b in singles if not _clean(simulate([b]))]
    if bad:
        fails.append(f"N-1 violated by single breakers: {bad}")

    reach = any(not simulate(d["controls_breakers"], 1.25)["converged"]
                or "overload" in simulate(d["controls_breakers"], 1.25).get("consequence", "")
                for d in devices().values() if d.get("controls_breakers"))
    if not reach:
        fails.append("no outage produces an overload — ratings are effectively unlimited")

    n0 = rated_case14()
    pp.runpp(n0)
    print(f"N-0 max line loading: {n0.res_line.loading_percent.max():.0f}% of rating "
          f"(N1_MARGIN={N1_MARGIN})")
    print(f"N-1 checked over {len(singles)} breakers")
    for f in fails:
        print("FAIL —", f)
    print("OK — ratings are N-1 secure and the overload path is reachable" if not fails else "")
    return 0 if not fails else 1


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--device", help="entities.yaml device id, e.g. RTU-3 (opens all its breakers)")
    ap.add_argument("--breaker", help="single breaker, e.g. BR-4-9")
    ap.add_argument("--all", action="store_true", help="simulate every RTU -> JSON files")
    ap.add_argument("--library", action="store_true",
                    help="enumerate every breaker subset x load level -> consequence_library.json")
    ap.add_argument("--load-scale", type=float, default=1.0,
                    help="scale all loads (stress the grid; 1.25 and 1.5 are useful)")
    ap.add_argument("--selfcheck", action="store_true")
    a = ap.parse_args()

    if a.selfcheck:
        return selfcheck()

    OUT_DIR.mkdir(parents=True, exist_ok=True)
    if a.library:
        lib = build_library()
        (OUT_DIR / "consequence_library.json").write_text(json.dumps(lib, indent=1))
        counts = collections.Counter(e["class"] for e in lib)
        print(f"{len(lib)} entries -> {OUT_DIR / 'consequence_library.json'}")
        for k, v in counts.most_common():
            print(f"  {k:10} {v:4}   ({len({e['consequence'] for e in lib if e['class'] == k})} distinct texts)")
        print(f"  DISTINCT consequence strings overall: {len({e['consequence'] for e in lib})}")
        return 0

    if a.all:
        for did, d in devices().items():
            if not d.get("controls_breakers"):
                continue
            res = simulate(d["controls_breakers"], a.load_scale) | {"device": did, "ip": d["ip"], "bus": d["bus"]}
            (OUT_DIR / f"consequences_{did}.json").write_text(json.dumps(res, indent=2))
            print(f"{did}: {res['consequence'][:80]}")
        return 0

    if a.device:
        d = devices()[a.device]
        res = simulate(d["controls_breakers"], a.load_scale) | {"device": a.device, "ip": d["ip"], "bus": d["bus"]}
    elif a.breaker:
        res = simulate([a.breaker], a.load_scale)
    else:
        ap.error("give one of --selfcheck / --device / --breaker / --all")
    print(json.dumps(res, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
