# Requests, decisions and filing-stage prediction

Kazi Rafsan Mahboob · October 30, 2026

The previous study established persistence in authorized returns. I now separate the utility's recorded request from the final award. The question is whether the earlier award is already associated with the request, and whether the request adds predictive information beyond the earlier award.

## Data and sample construction

The case source is the preserved [EEI 2025 Q3 workbook](../data/external/eei/source.json). Its [finance page](https://www.eei.org/issues-and-policy/finance-and-tax) was checked again on October 30. That page still links 2025 Q3 as the newest public rate-review workbook. `read_workbook` checks its fingerprint, sheet identities and published quarterly controls. The status `Settled` is a completion field here; it does not identify a negotiated settlement rather than a litigated decision.

Of 2,198 completed base-rate observations in 1980–2024, 1,785 have both requested and authorized ROE and valid filing dates. The paired table covers 50 jurisdictions and 1,694 distinct state/decision dates. It is a publisher-table dataset, not 1,785 independently coded original orders.

The 1985–2024 stage model uses 1,266 pairs with complete predictors. Adding an award known before filing leaves 1,135. The earlier 759-observation panel and this stage panel overlap on 753 IDs. Six earlier cases lack a recorded request. Different questions and inclusion rules produce different samples; these denominators are not interchangeable.

`panel.csv` keeps every candidate, inclusion flag, source row, docket, exact utility-state label, request, award and prior-decision IDs. No fuzzy utility-name matches or missing-value imputation are used. The existing 53-series economic archive is retained. An additional [Alabama unemployment history](../data/external/filing_2026-10-30/manifest.json) covers a state present in the pre-1985 descriptive table. It does not add a state to the primary regression sample.

## Chronology

The known prior is the mean observed award at the most recent date strictly before filing for the exact utility-state label. The maximum age is 3,652 days. Same-day awards and decisions made while the case was pending are excluded. Tied earlier awards retain every source ID. In 105 paired cases, the filing-stage prior identity differs from the authorization-stage prior. That count includes unavailable or stale filing priors and is not a count of 105 errors in the earlier study, which used a different reference date.

Filing and decision Treasury variables use preceding 90-calendar-day DGS10 means, with at least 40 observations and a final value no more than seven days earlier. Inflation and state unemployment use reference months two months earlier. Changes are decision-window values minus filing-window values. Duration is filing-to-decision days divided by 365.25, restricted to zero through 3,652 days. Reference dates and daily observation counts are retained.

The histories contain revisions. EEI also records a request and filing date without an amendment history. Its recorded request is not verified as the exact value available on the filing day. The new prediction exercise enforces chronology for prior awards and economic reference dates, but remains a retrospective comparison with recorded requests. It is not an unrevised, live-issued forecasting record.

## The stage decomposition

For each pair:

```text
authorized return = requested return + (authorized return - requested return)
```

I fit each of those three outcomes on the same observations and design matrix. Predictors are filing Treasury, inflation and unemployment; their changes through authorization; duration; and distribution status. The full paired sample uses state/year effects. The common prior sample adds the known prior, then replaces state effects with utility-state effects as a separate specification.

Linearity requires each award coefficient to equal the corresponding request coefficient plus the award-minus-request coefficient. The build asserts this identity for every parameter, including the fixed effects, to within 1e-9. The exported decomposition reports the model features. It allocates a conditional association between recorded stages; it does not identify a causal mediation effect. Requested returns are endogenous to a utility's information, objectives and expectations.

The utility-state specification combines fixed effects and a lagged outcome in irregular, short company histories. Dynamic-panel bias remains possible. Neither that coefficient nor a request coefficient should be interpreted as a structural adjustment speed or bargaining parameter.

## Uncertainty and weighting

Models use NumPy least squares and state plus authorization-quarter cluster covariance, subtracting the intersection covariance. Each component has its finite-sample correction. Approximate intervals use the t critical value with the smaller cluster count minus one. State-only and quarter-only results are exported as sensitivity checks. A negative feature variance is recorded as unavailable.

Every exact state/date/docket key is unique in the paired table, so weighting those keys would reproduce the row-weighted model. A conservative sensitivity instead gives every state/decision date total weight one after selecting the sample. That can combine unrelated proceedings. It is not a verified legal-case crosswalk. Cluster covariance uses the correctly weighted scores, tested against statsmodels WLS. State-omission checks refit the known-prior award model 49 times under state/year effects.

## Retrospective prediction

Evaluation filing-year blocks were fixed before estimation: 2000–2004, 2005–2009, 2010–2014, 2015–2019 and 2020–2022. Training observations were authorized strictly before January 1 of each block and filed since 1985. A block needs 100 complete training rows and a full-rank design. The 2000–2004 block has 389 training rows but no training variation in distribution status. It remains unavailable. No predictor was dropped to produce a comparison.

The remaining blocks contain 568 unique cases. All six rules use the same cases:

| Rule | Calculation |
|---|---|
| Known prior | Carry forward the award known before filing |
| Request | Use the recorded request directly |
| Request + historical gap | Add the training mean award-minus-request gap |
| Prior + historical change | Add the training mean award-minus-prior change |
| Market/prior model | Filing Treasury, inflation, unemployment, distribution, prior age and known prior |
| Model with request | Add the recorded request to the market/prior design |

Duration and changes after filing are excluded from prediction regressors. Coefficients remain fixed inside a block; known earlier awards can update between filings. The exports identify each training cutoff, last training decision and known-prior date. The ending filing year is 2022, allowing more time for decisions to appear in the source vintage, but the dataset still conditions on completed cases with recorded awards. It does not represent all filings or unresolved cases.

MAE and RMSE are expressed in basis points. Paired improvement is baseline absolute error minus candidate absolute error, so positive values favor the candidate. Its interval uses state/authorization-quarter clusters conditional on fitted models. Training estimation, source revisions, request amendments, model selection and sample censoring are outside that interval.

Two diagnostics were added after the first prediction calculation and are identified in the dated plan. One omits exact request/award matches; this outcome-based selection cannot be used as a prospective rule. The other omits each state from the saved error comparison. Neither diagnostic refits a model or changes the main predictions. Native R separately verifies the mean improvements, cluster standard errors and intervals for all 49 diagnostic rows.

## Run and inspect

```sh
python -m scripts.fetch_filing_sources
python -m src.filing_study
Rscript analysis/filing.R reports/filing-study
python -m src.filing_study --verify-r
python -m src.filing_study --check
python -m src.research serve --snapshot
```

Open `http://127.0.0.1:8765/presentation/filing.html`. The cream-and-black explorer filters real pairs by region, authorization year, utility, state and docket. It recalculates paired means, gaps and annual plots, and exports every selected row. It does not fit regressions in the browser or silently change the published findings. Empty selections remain empty. Source values are inserted as text, and CSV exports quote strings and neutralize spreadsheet formulas.

The R script independently rebuilds all 12 stage models, three covariance choices, 35 coefficient identities and six prediction rules. Prepared Stata syntax and Unicode datasets are included. Numeric DTA round trips are checked; native Stata execution remains unverified. The [analysis plan](filing_analysis_plan_2026-10-30.md) distinguishes initial decisions from the diagnostic changes after the first calculation. The [results](../reports/filing-study/README.md) contain the estimates and all supporting exports.
