# Market conditions and persistence in authorized utility returns

Analysis specification recorded October 26, 2026, before estimating this extension. The earlier period comparisons were already known. This is an analysis plan, not a preregistration.

## Questions

1. How are authorized electric utility ROEs associated with interest rates, inflation, broad financial stress, filing duration and case type?
2. Does the previous observed award for the same utility-state label add information after accounting for those variables?
3. Do the associations persist with state and year controls, utility-state and year controls, and within-group changes?
4. Do models fitted through 2019 improve on simple benchmarks when predicting recorded 2020–2024 awards?

## Population and timing

Use the preserved EEI 2025 Q3 electric table, completed distribution and vertically integrated cases only. The estimation period is 2010–2024, excluding the incomplete 2025 reporting year. A table observation is not necessarily a distinct contested proceeding. Preserve source worksheet rows, missing awards, utility labels and docket identifiers.

Use the October 26, 2026 historical macroeconomic vintage. These are reconstructed historical measurements, not an as-known information set. In particular, STLFSI4 is a revised index. Observation lags reduce accidental use of later dates but do not remove historical revisions.

* Treasury: arithmetic mean DGS10 over the 90 calendar days strictly before authorization; require at least 40 numeric observations and a last observation no more than seven days before authorization. Repeat with 30 days, at least ten observations.
* Yield curve: T10Y3M over the same windows and coverage rules, in percentage points.
* Inflation: CPIAUCNS year-over-year percentage change for the month two calendar months before authorization. Require both month levels. This is a conservative calendar lag, not a reconstruction of release timestamps.
* Financial stress: latest STLFSI4 observation dated at least 14 days before authorization, no more than 14 days before that cutoff. Units are index points. This is broad financial stress, not a utility credit spread or equity risk premium.
* Filing duration: elapsed days from request to authorization, divided by 365.25. Invalid, negative or greater-than-ten-year durations remain missing and are counted.
* Prior award: mean reported award at the most recent strictly earlier authorization date for the same exact utility label and state, no more than ten years earlier. Same-day entries never supply one another's prior award. Preserve prior row IDs, date, multiplicity and gap. This proxy measures recorded persistence, not a commission's use of precedent.
* Case type: distribution indicator. Do not infer settlement status from the publisher's `Settled` label.

## Estimation

The dependent variable is authorized ROE in percentage points. Main models share the complete-case sample for the four macro variables, filing duration and prior award. Estimate (1) market and case variables, (2) add prior award, (3) state and authorization-year fixed effects, and (4) exact utility-state and year fixed effects. Drop redundant constant categorical terms; fail on remaining rank deficiency. Report sample counts and exclusions, coefficients, R-squared and 95% normal-approximation Wald intervals with finite-sample-corrected two-way cluster covariance by state and authorization quarter. State clustering covers dependence within commissions and repeated utilities; quarter clustering allows common shocks. Display nonpositive variance estimates as unavailable, never replace them with zero. Report HC3 uncertainty as a sensitivity check.

Report Pearson and Spearman correlations with pairwise sample counts, and the main common-sample correlation matrix separately. Correlations and fitted slopes are associations. A causal claim would additionally require an identification design and credible exogeneity assumptions.

## Checks fixed in advance

* Replace 90-day market windows with 30-day windows, holding the main sample fixed where possible.
* Omit all New England observations; restrict to distribution cases.
* Add requested ROE in a separate complete-pair analysis, comparing models on the same restricted sample. The request is jointly determined with the proceeding; its coefficient is not a structural effect.
* Difference successive observations within exact utility-state groups in the estimation window, with gaps no greater than ten years; report both pooled and year-adjusted change regressions.
* Fit pooled market-and-case and prior-award-augmented models using 2010–2019 only. Evaluate on complete 2020–2024 rows against the training mean and last-observed-award baselines. Report MAE and RMSE in basis points, including negative improvements. This is a single temporal holdout, with no hyperparameter search.
* Recalculate core coefficients and correlations in native R from the exported panel and compare numerically with Python. Supply native Stata syntax without claiming Stata execution.

## Data refresh and publication

Keep the archived paper inputs fixed and hash every input. A separate tool can refresh the four whitelisted FRED series, preserve an entire complete retrieval, rebuild the dated joins and rerun selected calculations. A failed or incomplete refresh must not replace a previous complete snapshot. A refresh updates the macro vintage, not the EEI case population. No synthetic observations, imputed awards or invented independent ratings enter this analysis.
