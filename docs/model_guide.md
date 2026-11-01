# Explaining the models

This guide describes the current study. It is preparation for discussing the work, not evidence that the author has already mastered each method.

## What is being predicted?

The outcome is the authorized return on equity in a completed rate case. It is an allowed earnings opportunity, not the utility's realized stock return. A prediction of 9.75% against an award of 9.50% has an absolute error of 0.25 percentage points, or 25 basis points. Mean absolute error averages that distance across cases. It treats an overprediction and an equally large underprediction the same way.

The prior rule carries forward the most recent recorded award for the same utility-state label that was decided strictly before filing. The market/prior model adds filing-date Treasury, inflation, unemployment, case type and the age of that prior award. The final model adds the recorded request. Coefficients are fitted on decisions before an evaluation block and remain fixed during it.

Why must the prior precede filing? Suppose a case is filed in January and decided in December. An award issued in June was unavailable in January. Using it as January's prior would give the model later information.

## What do fixed effects do?

State effects allow states to have different average awards. Year effects allow each authorization year to have a different average. With both included, a coefficient compares observations after those average differences have been removed. A national variable that has one value per year is absorbed completely by year effects. The Treasury variable varies by case date within a year, so its coefficient is estimated from that remaining timing variation.

This is why the current stage model does not test the original national peer-anchoring question directly. Removing year effects restores annual variation, but also restores confounding by other national changes. A peer-average association will need trend and year-effect sensitivity checks, not just a regression with fewer controls.

Utility-state effects compare a utility-state history with its own average. Combining those effects with a lagged outcome introduces a dynamic-panel problem: subtracting a short group's estimated mean makes the lagged outcome correlated with the transformed error. In a standard short dynamic panel, the persistence coefficient is biased downward. Irregular case intervals and a selected prior make its size harder to characterize here. The estimate is not an adjustment-speed parameter.

## What is the stage comparison?

Award equals request plus award minus request. Regressing all three on the same observations and controls therefore makes their coefficients add in the same way. This is algebra, not independent evidence that the model is valid. Its economic use is to ask where the association appears: in the request, in the difference between request and award, or both.

The prior associations are 22.24 basis points for requests and 17.13 for awards. The difference of -5.11 has an interval spanning zero. There is evidence of continuity at both stages, but insufficient precision to argue that commissions systematically offset it.

## Why cluster uncertainty?

Cases in the same state can share commission practices. Cases decided in the same quarter can share national conditions. Two-way clustering allows residual dependence within either group. It changes estimated uncertainty, not the fitted coefficients. The implementation adds the state and quarter covariance estimates and subtracts the overlap. The reported intervals are approximate and depend on the available number of clusters.

Prediction-improvement intervals compare errors on the same cases. They condition on the fitted models. They do not account for refitting uncertainty, historical revisions or all decisions made while developing the analysis.

## What does the recent block mean?

For 2020–2022 filings, the prior alone has 21.93 basis points of error, versus 37.45 for market/prior and 24.43 with the request. This makes persistence a useful benchmark. It does not yet show a response to the 2022 rate shock: 40 of the 102 decisions occurred in 2020 or 2021. The [dated follow-up](research_review_2026-10-30.md) separates filing cohorts from decision timing.

Before presenting, explain why a low prediction error does not establish a causal mechanism; why all models must use the same evaluation cases; and why dropping a failed evaluation block or constant predictor after inspecting performance would change the stated design. Be able to reconstruct one case's prior date and one absolute-error calculation from the source.
