# How much does the model improve prediction?

Kazi Rafsan Mahboob · October 28, 2026

This is a post hoc evaluation of the predictions already saved in the October 26 study. It adds uncertainty, annual comparisons and weighting checks. It does not choose a new specification or fit another model on the evaluation period.

## Question and comparison

The main study found that adding the previous award reduces mean absolute error from 53.1 to 23.3 basis points relative to the market-and-case model. A simpler rule, carrying forward the previous award, has an error of 24.2 basis points. The important remaining question is whether the augmented model improves reliably on that simple rule.

For each of the same 188 observations, I calculate:

```text
paired improvement = |actual - reference prediction| - |actual - model prediction|
```

I convert percentage-point inputs to basis points before summarizing the errors. Positive improvement means the model has the smaller absolute error. All methods use the same observations. Missing predictions cannot be silently dropped, and the source IDs, authorization dates, actual returns and previous-award values must match the preserved estimation table.

## Uncertainty

I regress the paired loss difference on an intercept. Its coefficient is the mean improvement. The covariance uses state clusters plus authorization-quarter clusters minus their intersections, with the finite-sample corrections used in the main paper. This allows errors within a commission and errors sharing a quarter to move together. The saved evaluation contains 42 states and 20 quarters.

The reported 95% normal Wald interval is conditional on the already fitted models. It does not include uncertainty from fitting the training models, original-data revisions or choosing the specification. Twenty quarterly clusters are limited, so the interval is an approximate assessment rather than a guarantee of nominal coverage. The implementation uses the documented [statsmodels two-group cluster covariance](https://www.statsmodels.org/v0.14.4/generated/statsmodels.stats.sandwich_covariance.cov_cluster_2groups.html), and base R independently recomputes the covariance from grouped residual sums.

## Stability checks

- Annual and case-type tables retain the original models and show each group's observation count.
- Equal-utility-state weighting first averages each group's paired losses, then gives each group one vote. It answers a different weighting question from the main row-weighted estimate.
- The leave-one-state-out table omits each state in turn and recomputes the point estimate. This is an influence check, not a confidence interval or a search for a favorable sample.
- Win/loss counts show how often each method has smaller error. An average gain can occur even when the model loses on more individual observations, because the sizes of the errors differ.

These checks use the saved sequential retrospective predictions. A test-period row can use an earlier test-period award as its prior award, but no test-period outcome updates the fitted coefficients. The revised macroeconomic histories prevent a real-time forecasting interpretation. This evaluation is not a causal test of precedent or interest rates.

## Reproduce

From the repository root, after installing the normal Python dependencies:

```sh
python -m src.prediction_audit
Rscript analysis/prediction_audit.R reports/prediction-audit
python -m src.prediction_audit --verify-r
python -m src.prediction_audit --check
```

The first command checks the preserved factor-study fingerprints and writes new evaluation outputs. It leaves the original study unchanged. The R command independently recomputes four MAEs, four RMSEs, two paired improvements and two clustered standard errors. `--verify-r` compares those 12 values and records the artifact hashes. `--check` verifies the saved fingerprints and recomputes the numerical comparisons without writing files. CI checks the saved evaluation and runs the native R checks separately.

Use `--output /path/to/empty-folder` for another output location. The program refuses to overwrite a nonempty folder that is not an existing prediction-audit export. Rebuilding invalidates any earlier R check until R has been rerun.

See the [evaluation outputs](../reports/prediction-audit/README.md) for results, tables and figures, and the [main methods](factor_study.md) for the original sample and model construction.
