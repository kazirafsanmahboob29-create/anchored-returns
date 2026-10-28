# Market conditions and persistence in authorized utility returns

Kazi Rafsan Mahboob. October 26, 2026.

I examine whether national financial conditions and a utility's previous recorded award help explain variation in authorized electric utility returns. The contribution is a dated, source-linked panel with explicit timing rules, competing specifications and a retrospective temporal prediction check. The design estimates conditional associations. It does not identify a causal effect of interest rates or regulatory precedent.

## Inputs and observations

The EEI 2025 Q3 workbook supplies 777 completed electric distribution or vertically integrated observations in 2010–2024. There are 589 reported awards. The main complete-case sample contains 533 observations, 47 jurisdictions, 131 exact utility-state groups and 60 authorization quarters. The 244 excluded entries include 188 without an outcome. Missingness counts overlap: 106 lack an eligible prior award and one has an invalid or missing filing duration. Economic histories cover every observation under the specified rules. Excluded awards are not imputed.

The publisher table is retrospective. A row may be a formula implementation or one part of a common proceeding, rather than a separate contested order. The outcome is the reported authorized ROE, not a realized investor return. The original-order archive remains a separate source for interpreting performance adjustments, formulas and commission reasoning.

Four economic histories were retrieved on October 26, 2026: DGS10, T10Y3M, CPIAUCNS and STLFSI4. Exact URLs, source credits, byte hashes and retrieval times accompany the preserved files. The CPI values match the direct BLS API in all 189 months of January 2010–September 2025. This checks two delivery routes for the same underlying series. It is not independent measurement. The source review verified that EEI's newest linked Rate Review was still 2025 Q3 and that a fresh download matched the preserved workbook.

See the [analysis plan](factor_analysis_plan_v0.1.0.md) for complete timing and inclusion rules, and the [source review](factor_source_review_2026-10-26.md) for definitions, rights and revision policies.

## Specification

The outcome and percentage-rate predictors use percentage points. The baseline includes a prior-90-calendar-day Treasury mean, the similarly averaged Treasury term spread, CPI year-over-year inflation with two reference months of lag, broad financial stress with fourteen days of lag, filing duration in years and a distribution-case indicator. The next specification adds the previous recorded award. Two further models add state and year effects, then exact utility-state and year effects. All four use the same 533 complete observations.

For prior awards, I use the most recent strictly earlier authorization date within ten years for the same exact utility label and state. I average multiple reported awards on that earlier date and retain their row IDs. Eight main-sample observations have multiple earlier source rows. I do not use same-day authorizations as one another's lags. Renamings are not independently resolved.

Confidence intervals use a finite-sample-corrected two-way cluster covariance by state and authorization quarter, with a normal 1.95996 critical value. State clusters allow dependence within commissions, including repeated utilities. Quarter clusters allow common dated shocks. These choices do not ensure that every remaining source of dependence has been captured. Nonpositive diagonal variances are reported as unavailable. HC3 sensitivity estimates are included where defined. Unit-leverage cells make HC3 unavailable in the state/year and utility/year specifications; they are counted rather than assigned artificial standard errors.

## Findings

The Pearson correlation between prior and current awards is 0.793; the Spearman correlation is 0.777 on the same estimation sample. Correlation with the Treasury mean is 0.149. A high correlation between successive awards can reflect persistent utility risk, commission policy, formula design or direct reliance on prior awards. It does not distinguish those mechanisms by itself.

In the market-and-case model, a one-percentage-point higher Treasury yield is associated with 0.158 percentage points of higher allowed ROE, or 15.8 basis points. Adding the previous award reduces that slope to 11.8 basis points. With state and year effects, it is -0.3 basis points, with a 95% interval of -4.8 to 4.2 basis points. This large change shows that the pooled association is not stable to common-year and jurisdiction controls. Year effects absorb much of the movement in national interest rates, so the adjusted slope answers a narrower within-year question.

The previous-award coefficient is 0.631 in the pooled augmented model and 0.267 with state and year effects, with a 95% interval of 0.072–0.463. With utility-state and year effects, it is 0.235, with an interval of -0.025–0.495. The direction remains positive, but the latter interval includes zero. Sparse repeated observations and dynamic-panel bias limit a structural interpretation of the fixed-effect lag coefficient.

## Robustness and prediction

The 30-day window yields a state/year-adjusted prior-award coefficient of 0.269. Omitting New England yields 0.264. In distribution cases it is 0.384, although that subsample has 162 complete observations. Adding the requested ROE on a common 531-observation request-pair sample reduces the prior coefficient from 0.265 to 0.178. The request is jointly determined with the proceeding, so this is a conditional comparison rather than an exogenous explanation.

The within-utility-state change sample has 435 observations. The Treasury-change slope is 0.103 without year effects and 0.038 with year effects; the year-adjusted interval includes zero. This agrees with the main result that pooled market associations depend materially on how common time variation is handled.

For the temporal check, I estimate coefficients on 345 complete observations from 2010–2019 and evaluate 188 observations from 2020–2024. No later rows enter coefficient estimation. Each test row's prior award may be an earlier test-period decision, so this is sequential retrospective evaluation, not a forecast issued once in 2019. Revised historical macro data also prevent interpreting it as a real-time forecasting exercise.

| Predictor | Mean absolute error, bp | Root mean squared error, bp |
|---|---:|---:|
| Training mean | 42.2 | 59.9 |
| Previous award | 24.2 | 35.8 |
| Market and case model | 53.1 | 69.9 |
| Model including previous award | 23.3 | 32.3 |

Previous awards contain useful predictive information beyond the market-and-case model. The augmented model improves MAE by only 0.9 basis points over the previous-award baseline, and RMSE by 3.5 basis points. The evidence favors including persistence in the investigation. It does not support claiming a large predictive advantage over that simple baseline.

## Reproduction and live calculations

```
./research national
./research factors
Rscript analysis/factors.R reports/factor-study
python -c 'from src.factor_study import package; package()'
./research overview
```

Python writes the full panel, complete-case panel, change panel, Stata table, correlation matrix, coefficients, holdout predictions and source fingerprints. Base R independently reproduces 27 coefficient/clustered-standard-error pairs and both prior-award correlations before creating the figures. Native Stata syntax is supplied; no Stata execution is claimed.

The browser workbench fits OLS by reorthogonalized QR and independently calculates the same two-way covariance, correlations and timing joins. Calculation exports include the selected rows, specification, vintage and input fingerprints. Tests compare browser numerical output with Python on the actual archived panel.

The optional standalone service’s `/api/factors/refresh` operation retrieves the four FRED public CSV histories and uses the direct BLS CPI API with a dated response cache. BLS responses are reused for 24 hours; if that API is unavailable, a preserved response no more than 45 days old can check overlapping months. The export and interface show its retrieval time and any unmatched new months. A numerical disagreement still rejects the retrieval. This avoids presenting an older validation response as a new API call. The connector validates series identities, dates, numeric values, coverage, freshness and CPI agreement. Complete raw source files and the parsed snapshot are saved before a latest pointer advances. Failed retrievals retain the previous complete snapshot. A fifteen-minute cache limits repeated upstream requests. FRED's keyless CSV export is a live data feed; it is distinct from FRED's authenticated observations API. Refreshing changes the macro vintage, not the case table or published paper.

This remains an observational investigation. A stronger causal extension would require a credible shock or regulatory discontinuity, original release vintages and a design that separates the shock from concurrent changes. Complete original-order coding and independently supplied ratings address a different question: the reasons commissions state for their decisions. They are not substituted with model predictions.

The Dartmouth WordPress edition runs the browser model directly and retrieves Treasury XML and BLS CPI without a separate application host. These endpoints permit cross-origin requests. Its refreshed run uses Treasury par yields and BLS CPI, while STLFSI4 retains the explicitly identified October 26, 2026 vintage. The archived paper uses the original FRED histories. Raw responses, source URLs and hashes are exported with each browser snapshot. See [WordPress deployment](dartmouth_portfolio.md) for the implementation and hosting boundaries.
