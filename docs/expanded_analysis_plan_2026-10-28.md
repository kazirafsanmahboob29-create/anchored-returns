# Historical expansion and award adjustment

Kazi Rafsan Mahboob · October 28, 2026

I set out this extension before estimating its new models. The October 26 study and October 28 prediction audit remain fixed. This extension uses additional historical cases from the same EEI workbook, longer economic histories and a new state-level variable. It is a planned extension of an existing investigation, not a preregistered study.

## Questions

1. Does the relationship between prior and current awards persist across a longer period?
2. Do changes in Treasury yields between successive decisions accompany changes in the same utility's allowed return?
3. Do rate increases and decreases have different associations with award adjustments?
4. Are regional differences still visible after accounting for case composition and year effects?
5. Does a more detailed model predict later cases better than carrying forward the last recorded award across several evaluation windows?

## Population and sources

The primary window is 1995–2024. Use completed electric distribution and vertically integrated observations from EEI's 2025 Q3 workbook. Keep its source rows and exact utility-state labels. An EEI row is a publisher observation, not an additional independently reviewed PDF. Keep 2025 observations outside the main analysis because the workbook covers only three quarters of that year.

Use DGS10, T10Y3M, CPIAUCNS and STLFSI4 from FRED, with their original producing agencies recorded. Add BLS seasonally adjusted state unemployment rates, distributed by FRED. Retrieve the histories into a new dated directory, validate series identities and preserve raw responses and hashes. Use the Census Bureau's state names, postal codes and four-region classification. No approximate utility-name matching or imputed awards are allowed.

## Timing and completeness

Treasury and curve variables are means over the 90 calendar days strictly before authorization. Require at least 40 numeric observations and a final observation within seven days. CPI inflation uses the reference month two calendar months earlier and its year-earlier value. State unemployment uses that same two-month lag. Financial stress uses the latest week ending at least 14 days earlier, with a maximum additional 14-day gap.

The prior award is the mean of awards at the strictly earlier, most recent decision date for the exact utility-state label, within ten years. Same-day observations cannot be each other's prior award. Retain all prior source IDs. Change variables compare economic conditions at the current and actual prior decision dates, including prior dates outside the estimation window. Report missingness and exclusions rather than replacing missing values.

These are revised historical series. Date lags do not recreate real-time information sets.

## Models

Estimate the original market-and-case and prior-award specifications on a common complete sample, then add state unemployment. Report pooled, state/year and utility-state/year versions. Show a 2010–2024 bridge comparison on the new input vintage. Add a longer 1985–2024 robustness analysis omitting financial stress, whose history starts later; compare models within that sample rather than treating its results as the same estimand.

For award changes, regress current minus prior ROE on changes in Treasury yields, the yield curve, inflation, financial stress and state unemployment, with the interval between awards and the distribution-case indicator. Report pooled and state/year versions. Replace the Treasury change with its positive and negative parts for an asymmetry specification and test equality of their slopes. Report a four-region interaction model and its joint test, without selecting regions according to their results.

Use ordinary least squares, check design rank and numerical conditioning, and calculate state plus authorization-quarter cluster covariance minus the intersection covariance. Apply finite-sample corrections and t intervals using the smaller cluster count minus one. These remain approximate observational intervals. Report unavailable negative-variance intervals explicitly. Cross-check coefficients and covariance in statsmodels and base R. Provide Stata syntax and round-trip checked DTA files without claiming native Stata execution.

## Prediction and sensitivity

Use expanding training windows beginning in 1995 and five fixed evaluation blocks: 2000–2004, 2005–2009, 2010–2014, 2015–2019 and 2020–2024. Fit coefficients using only earlier years. Compare the training mean, prior award, market-and-case model and prior-augmented model on identical observations within each block. Require at least 100 training observations; report any unavailable block. Do not tune the specification using evaluation errors. Earlier evaluation-period decisions may supply lagged awards but cannot update fitted coefficients.

Report all blocks, annual and regional denominators, paired loss improvements and uncertainty. Include the share of unchanged awards and the distribution of adjustments. Regional summaries describe this table, rather than a census of all commission decisions. Correlations and model coefficients do not by themselves identify the effect of precedent or interest rates.

## Outputs

Preserve raw inputs, a row-level inclusion table, estimation and change panels, model specifications, coefficients, predictions, regional summaries and source fingerprints. Keep the extension separate from the original reports. Reusable NumPy modules should handle date-window joins and clustered calculations; tests must compare them with direct calculations and existing statistical implementations. R should independently reconstruct designs from exported data. Stata files should use the same stated specifications and covariance corrections.

## Diagnostics added after the initial estimates

The first estimates showed a regional interaction and a change in prediction performance over the longer period. I therefore add two explicit sensitivity checks: state-only and quarter-only covariance for every model, using the same conservative t critical value, and omission of each state in turn for the state/year prior-award model and regional interaction model. Report every omission, including failures to estimate. These are post-estimation diagnostics, not newly preregistered tests. Retain the primary specifications and all original evaluation blocks.
