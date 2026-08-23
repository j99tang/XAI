"""Cross-judge sensitivity (plan Matrix 3): does the CPAS ordering survive a different judge?

WHAT THIS IS NOT. This is not the human-agreement check. It asks whether the result is
robust to the choice of grading model — it cannot tell you whether CPAS tracks what a
human expert would call quality. If language models share a bias they will agree with
each other and human agreement remains unmeasured. Report it as judge sensitivity.

INDEPENDENCE. The second judge must not be either run's synthesizer, or it grades its own
output (self-preference measured as quality). Primary judge = claude-opus-5; synthesizers
are llama3.1:8b and openai/gpt-5.5; so the second judge is a Gemini-class model.

Scores the SAME blind 20-item sample the human worksheet uses, so the three are directly
comparable if you later fill in the sheet.

Run: conda run -n xai python scripts/judge_sensitivity.py [--model <openrouter id>]
"""
from __future__ import annotations
import importlib.util, json, os, sys, time
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))
from dotenv import load_dotenv                                    # noqa: E402
load_dotenv(ROOT / ".env")
from caie.evaluation.judge import RUBRIC, PERSONA_EXPECT, SCHEMA, DIMS, cpas  # noqa: E402

spec = importlib.util.spec_from_file_location("hs", ROOT / "scripts/human_score.py")
hs = importlib.util.module_from_spec(spec); spec.loader.exec_module(hs)

MODEL = "google/gemini-3.1-pro-preview"
if "--model" in sys.argv:
    MODEL = sys.argv[sys.argv.index("--model") + 1]
OUT = ROOT / "experiments" / "results" / f"judge_sensitivity_{MODEL.replace('/','-')}.json"
RATE_DELAY = float(os.environ.get("CAIE_JUDGE_DELAY", "7"))   # seconds between calls
BANNED = ("llama-3.1-8b", "llama3.1:8b", "gpt-5.5")   # the two synthesizers under test


def main() -> None:
    if any(b in MODEL for b in BANNED):
        raise SystemExit(f"{MODEL} is a synthesizer in this experiment — it would grade its "
                         f"own output. Pick a judge that wrote none of the narratives.")
    from openai import OpenAI
    client = OpenAI(base_url="https://openrouter.ai/api/v1",
                    api_key=os.environ.get("CAIE_SYNTH_KEY") or os.environ["OPENROUTER_API_KEY"])

    items = hs.sample()
    primary = {}
    for run in hs.RUNS:
        for r in json.load(open(ROOT / f"experiments/results/{run}/cpas_scores.json"))["rows"]:
            primary[f"{run}|{r['scenario']}|{r['tier']}|{r['persona']}"] = r

    out = json.loads(OUT.read_text()) if OUT.exists() else {}
    for n, (run, sid, tier, persona) in enumerate(items, 1):
        key = f"{run}|{sid}|{tier}|{persona}"
        if key in out:
            continue
        gold = json.loads((ROOT / f"experiments/scenarios/{sid}.json").read_text())["gold_facts"]
        nar = (ROOT / f"experiments/results/{run}/{sid}_{tier}_{persona}.txt").read_text()
        user = (f"{RUBRIC}\n\nPERSONA the narrative was written for: {persona}\n"
                f"WHAT THIS PERSONA WAS ASKED TO PRODUCE (score R and A against this):\n"
                f"{PERSONA_EXPECT[persona]}\n\nGOLD FACTS (ground truth):\n"
                f"{json.dumps(gold, indent=2)}\n\nNARRATIVE TO GRADE:\n{nar}\n\n"
                f"Return ONLY a JSON object with integer keys D, C, A, R (1-5) and H (0 or 1). "
                f"No other text.")
        # Retry: OpenRouter routes vary, and a route can return empty content or
        # non-JSON. Skipping silently would quietly shrink n and bias the sample toward
        # whatever this judge finds easy to score.
        # New OpenRouter accounts are capped (e.g. 10 rpm on gpt-5.4). Pace requests so
        # a rate limit does not silently shrink n -- a partial sample here is worse than
        # a slow one, because agreement on 10 arbitrary items is not agreement.
        time.sleep(RATE_DELAY)
        parsed = None
        for attempt in range(3):
            try:
                r = client.chat.completions.create(
                    model=MODEL, temperature=0, max_tokens=4000,
                    response_format={"type": "json_object"},
                    messages=[{"role": "user", "content": user}])
                txt = (r.choices[0].message.content or "").strip()
                if not txt:
                    raise ValueError(f"empty content (finish={r.choices[0].finish_reason})")
                obj = json.loads(txt[txt.index("{"):txt.rindex("}") + 1])
                parsed = {d: int(obj[d]) for d in DIMS}
                break
            except Exception as e:
                msg = str(e)[:80]
                print(f"    retry {attempt+1}/3 on item {n:02d}: {type(e).__name__}: {msg}",
                      flush=True)
                time.sleep(RATE_DELAY * 2 if "429" in str(e) else 2)
        if parsed is None:
            print(f"  {n:02d} FAILED after 3 attempts — excluded from n"); continue
        out[key] = parsed
        OUT.write_text(json.dumps(out, indent=1))
        print(f"  {n:02d}/{len(items)} {persona:15} "
              f"2nd judge D{out[key]['D']} C{out[key]['C']} A{out[key]['A']} "
              f"R{out[key]['R']} H{out[key]['H']}   "
              f"| primary D{primary[key]['D']} C{primary[key]['C']} A{primary[key]['A']} "
              f"R{primary[key]['R']} H{primary[key]['H']}", flush=True)

    # agreement
    from scipy.stats import spearmanr
    import statistics as st
    keys = [k for k in out if k in primary]
    print(f"\n=== judge sensitivity: {MODEL} vs claude-opus-5, n={len(keys)} ===")
    print(f"{'dim':>4} {'Spearman':>10} {'exact':>8} {'within1':>9} {'mean Δ':>8}")
    for d in "DCAR":
        a = [out[k][d] for k in keys]; b = [primary[k][d] for k in keys]
        rho = spearmanr(a, b).correlation if len(set(a)) > 1 and len(set(b)) > 1 else float("nan")
        print(f"{d:>4} {rho:>10.3f} {sum(x==y for x,y in zip(a,b))/len(a):>7.0%} "
              f"{sum(abs(x-y)<=1 for x,y in zip(a,b))/len(a):>8.0%} "
              f"{st.mean(b)-st.mean(a):>+8.2f}")
    a = [out[k]["H"] for k in keys]; b = [primary[k]["H"] for k in keys]
    print(f"{'H':>4} {'(binary)':>10} {sum(x==y for x,y in zip(a,b))/len(a):>7.0%} "
          f"{'':>8} {st.mean(b)-st.mean(a):>+8.2f}")
    # --- same-family bias check -------------------------------------------------
    # A judge from the same family as one run's synthesizer may prefer its sibling's
    # output. Split agreement by which model WROTE the narrative: if this judge is
    # systematically kinder to gpt-5.5's narratives than the cross-vendor judge is,
    # that is self-preference showing up as quality.
    fam = [k for k in keys if "gpt-5.5" in k]
    oth = [k for k in keys if "gpt-5.5" not in k]
    if fam and oth:
        def gap(ks):
            return st.mean(sum(out[k][d] for d in "DCAR") - sum(primary[k][d] for d in "DCAR")
                           for k in ks)
        print(f"\n  SAME-FAMILY BIAS CHECK (this judge vs claude-opus-5, sum of D+C+A+R):")
        print(f"    on gpt-5.5-authored narratives (n={len(fam)}): {gap(fam):+.2f}")
        print(f"    on other narratives            (n={len(oth)}): {gap(oth):+.2f}")
        print(f"    difference: {gap(fam)-gap(oth):+.2f}  "
              f"(a large positive value = this judge favours its own family)")
    print("\n  mean Δ > 0 -> the PRIMARY judge (claude-opus-5) scores higher.")
    print("  Does the tier ordering survive? (mean CPAS by tier, second judge)")
    for t in ("A", "B", "C"):
        v = [cpas(out[k]) for k in keys if k.split("|")[2] == t]
        if v:
            print(f"    tier {t}: {st.mean(v):.2f}  (n={len(v)})")


if __name__ == "__main__":
    main()
