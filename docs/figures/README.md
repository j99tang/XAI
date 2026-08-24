# Figures

Regenerate all five: `conda run -n xai python scripts/make_figures.py`
(reads `experiments/results/*/cpas_scores.json`; no API cost).

| file | claim it carries | pairs with |
|---|---|---|
| `fig1_capability_gradient.png` | Context helps at every capability level; a gradient, not a threshold. Tiers A and B are flat at ~1.5 across all six models — and since those narratives are byte-identical between rows, that flatness doubles as an independent judge-consistency check. | T1 |
| `fig2_reliability_separates.png` | Raw substance is similar across models (3.02–4.04); the hallucination rate is not (38%→4%). Reliability, not eloquence, is the deployment constraint. | T1, T2 |
| `fig3_tier_ablation.png` | A<B<C by persona, floor vs ceiling. Shows the regulator flat at the 8B and transformed at the ceiling. | T3, T4 |
| `fig4_regulator_penalty.png` | Why the regulator is flat: raw 2.96 with H=73%, so λ·H erases the entire gain. The persona that gains most from context is the one most exposed to unreliability. | T3 |
| `fig5_lambda_sensitivity.png` | Model ordering is unchanged at λ = 0,1,2,3 — the conclusion does not depend on the pre-registered λ=2. | T6 |

## Suggested slide order

1. **fig1** — the headline. Two flat lines and one rising one.
2. **fig3** — break it out by role.
3. **fig4** — the surprise: the regulator *does* benefit; unreliability takes it back.
4. **fig2** — generalise it: reliability is what separates models.
5. **fig5** — pre-empt "why λ=2?" before it is asked.
