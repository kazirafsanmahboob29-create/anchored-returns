# Historical expansion: methods and tools

Kazi Rafsan Mahboob · October 28, 2026

The extension examines 1995–2024 using a longer history of EEI cases and economic conditions. I retain the original 2010–2024 study as a separate release and verify that its 533 case IDs remain in the common-period sample. The new primary sample contains 759 complete observations across 48 jurisdictions and 147 utility-state labels. The [analysis plan](expanded_analysis_plan_2026-10-28.md) distinguishes the initial specifications from diagnostics added after the first estimates.

## Observations and inclusion

EEI's 2025 Q3 workbook is the case source. I use its completed electric distribution and vertically integrated observations. The 1995–2024 candidate table has 1,195 rows, including 899 observed allowed returns. Missing awards, missing prior awards and incomplete predictors reduce the main estimation sample. The field-level counts overlap, so they cannot be added to recover the total exclusions. `panel.csv` retains the inclusion flags and all source row IDs.

The change models use 717 observations with an actual earlier award and financial conditions matched at both decision dates. This is a separately defined sample, since these models use the interval between awards rather than filing duration. A longer 1985–2024 sample contains 1,141 complete observations when financial stress is omitted. I estimate matched specifications without stress in the primary period as well, so a difference between windows is not confused with simply adding or removing that variable.

An observation is a publisher-table entry. Joint proceedings and repeated companies are present. These rows are not 759 independently reviewed commission PDFs. Exact utility-state labels define entities. I do not silently combine renamed companies or treat same-day awards as a sequence.

## Economic variables

The [source guide](expanded_sources.md) documents the 53 preserved series and Census mapping. For each authorization date:

- `treasury90`: mean DGS10 over the preceding 90 calendar days, excluding the decision day.
- `curve90`: mean T10Y3M over the same window.
- `inflation`: 12-month CPI change, using the reference month two calendar months earlier.
- `stress`: the latest STLFSI4 observation at least 14 days earlier, allowing a further gap of at most 14 days.
- `unemployment`: the seasonally adjusted state rate for the reference month two months earlier.
- `duration`: filing-to-authorization days divided by 365.25, restricted to zero through 3,652 days.
- `prior`: mean award at the strictly earlier, most recent date for the exact utility-state label, within 3,652 days.

The daily windows require at least 40 numeric observations and a final observation within seven days of authorization. Missing source values remain missing. `prior_ids`, `prior_date`, current reference dates and previous reference dates make each lag traceable. Changes use conditions at the actual prior date, even when that date falls outside the estimation period.

All histories contain later revisions. Timing rules prevent same-day joins but do not recreate the information available in real time.

## Estimation and uncertainty

`panel_models.py` uses NumPy least squares, a QR-based inverse for the covariance calculation, and explicit checks for finite inputs, rank and residual degrees of freedom. State/year and utility-state/year designs use ordinary indicator variables. The exported `model_specs.csv` identifies each target, predictor list, sample and fixed-effect choice.

The primary covariance is state-cluster covariance plus authorization-quarter covariance minus their intersection covariance. Each component has its finite-sample correction. Intervals use the t critical value with the smaller cluster count minus one. State-only and quarter-only sensitivity columns use the same critical value. These intervals remain approximate.

The utility-state models also combine fixed effects with a lagged outcome in short, unbalanced case histories. That can bias a dynamic-panel coefficient. I report the estimate as an association, rather than as a structural speed of regulatory adjustment. The prediction comparisons provide a separate assessment of whether the earlier award is useful.

Two-way covariance can be indefinite, particularly for the many fixed-effect coefficients. The model coverage file reports its minimum eigenvalue. A reported feature interval requires nonnegative variance. A joint test requires a positive definite covariance matrix for its restrictions. The code records an unavailable test rather than forcing a negative eigenvalue to zero. This matters for the Michigan omission in the regional diagnostic.

The asymmetry model separates positive and negative Treasury changes and tests equality of their slopes. The regional model interacts Treasury changes with the four Census regions and tests equality of those slopes. Joint tests use the cluster covariance and an approximate F reference distribution. The region estimates describe conditional associations in this case table.

## Prediction evaluation

The expanding training history begins in 1995. Evaluation blocks are fixed at 2000–2004, 2005–2009, 2010–2014, 2015–2019 and 2020–2024. A block requires at least 100 earlier complete observations. The first has only 65, so it remains explicitly unavailable. The four available blocks contain 634 unique predictions.

Each block compares the training mean, previous award, market-and-case model including unemployment, and the same model with the prior award added. Every method uses the same observations. Coefficients stay fixed within a block. A known earlier award during an evaluation block may serve as the next case's prior award. No evaluation outcome updates the fitted coefficients.

Errors are expressed in basis points. Positive paired improvement means the augmented model has smaller absolute error. The aggregate interval conditions on the fitted models and uses state and authorization-quarter clusters. It excludes model-selection and training-estimation uncertainty. Revised inputs make this a retrospective evaluation.

## Reproduce

```sh
python -m src.expanded_study
Rscript analysis/expanded.R reports/expanded-study
python -m src.expanded_study --verify-r
python -m src.expanded_study --check
```

`make expanded` runs the build and R cross-check. The R script reconstructs the designs independently from `panel.csv` and the specification table. It checks 111 coefficient/standard-error/interval rows, 222 alternative-covariance rows, six joint-test rows, four regional slopes and 634 predictions under each of four rules. `--check` verifies file fingerprints and recalculates the complete numerical study, including every state omission.

Stata replication is prepared in [analysis/expanded.do](../analysis/expanded.do). It uses built-in commands, the exported specification table and Unicode DTA files. Exported numeric values and IDs are round-trip checked in Python. Native Stata execution remains unverified.

## Explore a region or period

```sh
python -m src.expanded_study --explore levels --region Midwest --start 2010 --end 2024
python -m src.expanded_study --explore changes --region Northeast --start 2005 --end 2024 --export /tmp/northeast-changes.csv
```

The explorer selects the real rows, reports candidate and complete counts, and estimates the corresponding state/year model where the selected data permit it. It identifies the calculation as exploratory. An unsupported or rank-deficient selection returns a specific reason rather than a fabricated coefficient. CSV exports retain the source and prior-decision identifiers. Existing files and the published report directory cannot be overwritten through this command.

## Code checks

The window-index tests compare NumPy joins with direct date filtering, including zero, missing, stale and same-day values. Regression tests compare coefficients and covariance with statsmodels. Other tests check previous-date ties, preservation of the original case IDs, training/evaluation separation, source-retrieval failure, region filters and Stata exports. The [join benchmark](../reports/expanded-study/join-benchmark.json) reconciles all 759 complete cases before reporting its local timing.

See the [results](../reports/expanded-study/README.md) for findings and all published tables.
