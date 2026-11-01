# What other-state awards add

Recent other-state awards track the next allowed return, but much of their information is already present in the utility's own award history. This comparison separates the historical association from the additional value of using peers in a prediction.

The [working paper](../../paper/manuscript.md) places the result alongside the request and financing comparisons.

## Historical association

The peer measure averages completed awards in other states over twelve months strictly before filing. Each state and decision date receives equal total weight. A window needs ten awards from five other states. The regression comparison uses the same 1,109 complete cases throughout.

| Time controls with state effects | Peer association, bp per one percentage point | Approximate 95% interval |
|---|---:|---:|
| None | 35.35 | 22.84 to 47.86 |
| Linear decision-year trend | 38.30 | 24.48 to 52.13 |
| Separate decision-year effects | 15.41 | -5.74 to 36.56 |

The positive association persists with a linear trend, alternative weighting and a six-month window. Year controls absorb common annual changes, leaving a smaller and less precise estimate. The own prior and peer average have a correlation of 0.918, consistent with their containing much of the same historical information.

## Additional forecasting information

| Rule on the same 568 evaluation cases | Average absolute error, bp |
|---|---:|
| Prior only | 31.82 |
| Market conditions and prior | 33.09 |
| Market conditions, prior and peers | 32.09 |

These models are refitted on peer-available training records. The one-basis-point gain from adding peers has an approximate conditional 95% interval of -0.42 to 2.41. The results favor the own prior as a compact benchmark; the national peer average adds little forecasting information in this comparison.

## Tables and checks

[Study results](study.json) · [Coefficients](coefficients.csv) · [Model coverage](models.csv) · [Prediction comparisons](prediction_comparisons.csv)

Python and native R agree on the model coefficients and prediction comparisons. R uses the prepared peer variables; separate fixtures check the date windows and weighting. Case-level and prediction rows are generated locally after source acquisition. The [reproduction guide](../../docs/REPRODUCIBILITY.md) supplies the commands, and the [dated review plan](../../docs/research_review_2026-10-30.md) records the extension's selection rules.

## Interpretation

The peer association can reflect shared financing conditions, policy trends and case composition as well as regulatory comparisons. The prediction interval conditions on the fitted rules. The peer test is a post-review extension of the earlier study, with its date and prior exposure recorded in the plan.
