# Requests, decisions and persistence: analysis plan

Kazi Rafsan Mahboob · October 30, 2026

I wrote this plan after inspecting source coverage and before estimating the new models. It is a dated research record, not an external preregistration. The earlier numerical studies remain unchanged.

## Questions

1. How do requested and authorized returns differ across the historical case table?
2. How much of the association with an earlier award is already present in the utility's request?
3. Does a request improve retrospective prediction when the comparison uses information dated before filing?

The second question is an accounting and regression decomposition. It cannot identify bargaining power, commission preferences or a causal mediation effect. A request is an endogenous choice.

## Samples and timing

Use completed electric distribution and vertically integrated entries in the preserved EEI 2025 Q3 workbook. Keep 1980–2024 for descriptive request/award pairs. Use 1985–2024 for regressions to allow economic histories and prior decisions to accumulate. Report every exclusion and the overlap with the 759-observation historical model. No synthetic cases or imputed awards enter the analysis.

For each filing, use the most recent observed award for the exact utility-state label strictly before the filing date, with a maximum age of 3,652 days. Average tied awards at that earlier date and retain their IDs. Do not use a decision issued after filing as the filing's prior award. Record how often that distinction changes the prior used by the previous authorization-date study.

Use existing preserved Treasury, CPI and state-unemployment histories. Treasury is the preceding 90-calendar-day mean with at least 40 observations and a final observation within seven days. Inflation and unemployment use reference months two months earlier. Preserve filing and decision reference dates. Revised histories do not reproduce the information vintage available at filing.

## Models and decomposition

The full paired model uses filing Treasury, filing inflation, filing unemployment, their changes from filing to authorization, filing-to-decision duration and distribution status. Estimate request, award and award-minus-request outcomes on the same rows and predictor matrix, with state and year effects. A second common sample adds the known prior award; also report utility-state/year effects for that sample.

For identical designs, the award coefficients must equal request coefficients plus award-minus-request coefficients. This identity checks the calculations and attributes a conditional association between the two recorded stages. It does not establish why either party chose a number. Report two-way state/authorization-quarter covariance, one-way sensitivity and approximate t intervals.

Publisher rows can share proceedings. Report exact state/date/docket groups and a sensitivity assigning each such group equal total weight. Do not merge utility names using fuzzy matches. Use state omissions for the prior association under state/year effects. Flag rank failures and negative feature variances rather than forcing a usable estimate.

## Prediction

Fix evaluation filing-year blocks at 2000–2004, 2005–2009, 2010–2014, 2015–2019 and 2020–2022. Training cases must be authorized strictly before January 1 of the block and filed since 1985. Require 100 complete training rows. Test the same complete rows under six rules: known prior award; requested award; request plus mean training award-minus-request gap; prior plus mean training award-minus-prior change; a market/prior model; and that model with the request added.

Prediction regressors are filing Treasury, inflation, unemployment, distribution status, age of the known prior and the known prior award. Duration and decision-date financial changes are excluded. Coefficients remain fixed within each block. Known prior awards may update between filings within a block. Export actual training cutoff and prior dates. Report each block, aggregate MAE/RMSE and paired conditional uncertainty. The sample contains completed cases and revised inputs; this is not a deployed prospective forecast or a sample of all filings.

## Reporting and validation

Keep all specified models and available prediction blocks, including weak or contradictory results. Do not choose the preferred sample after comparing p-values. Native R must reconstruct the designs and predictions independently. Prepare Stata replication without claiming it ran if no installation is available. Add tests for strict filing chronology, exact decomposition, group weighting and training/test separation.

Present findings in a short technical case study with a source-linked case explorer. Filters describe the selected rows; they do not silently re-estimate or replace the published models. Use restrained typography and a cream-and-black layout. Keep the original document-coding work separate.

## Source decisions

EEI's public finance page was checked again on October 30 and still links 2025 Q3 as its newest rate-review workbook. Federal Reserve H.15 and BLS LAUS definitions were also checked. Moody's Baa spread data were considered but excluded because the FRED notes restrict redistribution. No proprietary bond history is added to the public repository. EIA utility matching would require a separately verified crosswalk and is outside this extension.

## Diagnostic changes after the first calculation

The exact state/date/docket key identified 1,785 distinct keys among the 1,785 pairs, so equal-weighting those keys changed nothing. I replaced that redundant sensitivity with equal total weight per state/decision date. There are 1,694 such dates. This conservative grouping can combine unrelated cases and is not a claim to identify legal proceedings. The primary row-weighted models are retained.

The first prediction block has sufficient rows but no variation in distribution status in its training set. It is retained as unavailable because the planned design lacks rank. No predictor was dropped to obtain an estimate. The added Alabama unemployment history covers a jurisdiction present only in the earlier descriptive cases; it does not expand the primary 1985–2024 regression sample.

The workbook does not preserve request amendment histories. The forecast comparison therefore uses the recorded request, with its exact filing-date availability unverified. The date restrictions establish chronology for prior decisions and economic reference windows. They do not establish an unrevised, real-time information set for every predictor.

After the first prediction results, I added two checks of the saved predictions: exclude exact request/award matches, and omit each state in turn. These do not refit models. The first conditions on an observed outcome and is a diagnostic, not a deployable selection rule. Both checks are reported even if they weaken the aggregate result.
