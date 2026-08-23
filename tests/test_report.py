"""Exercise the report plumbing with synthetic scores -- no API calls."""
import sys, json, random, statistics; sys.path.insert(0, "src")
from ccir.evaluation.report import paired_test

random.seed(0)
def rows_for(gap):
    out = []
    for i in range(30):
        base = random.uniform(1.0, 2.0)
        for t, bump in (("A", 0.0), ("B", gap/2), ("C", gap)):
            for p in ("operator", "data_scientist", "regulator"):
                out.append({"scenario": f"scenario_{i:02d}", "tier": t, "persona": p,
                            "cpas": base + bump + random.uniform(-0.15, 0.15), "H": 0,
                            "consequence_class": "OVERLOAD"})
    return out

print("clear effect (gap 1.0):"); print("  ", paired_test(rows_for(1.0), "A", "C"))
print("no effect (gap 0.0):");    print("  ", paired_test(rows_for(0.0), "A", "C"))

# pseudoreplication guard: 30 scenarios x 3 personas must report n=30 pairs, not 90
msg = paired_test(rows_for(1.0), "A", "C")
assert "n=30 pairs" in msg, f"unit of analysis is wrong: {msg}"
# too few pairs must decline to test rather than emit a bogus p-value
few = [r for r in rows_for(1.0) if r["scenario"] < "scenario_04"]
assert "too few pairs" in paired_test(few, "A", "C")
print("\nok -- pairs by scenario (n=30, not 90); declines when underpowered")
