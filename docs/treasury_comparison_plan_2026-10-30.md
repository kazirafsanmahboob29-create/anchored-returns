# Comparing the Treasury estimates

October 30, 2026. This diagnostic was specified after feedback on the working paper, before estimating the additional comparisons. It is a post hoc explanation of differences between existing models, not a new confirmatory test.

The filing-stage award model reports a Treasury association near 21 basis points per percentage point. The earlier decision-date state/year model reports an association near zero. These estimates use different periods, timing rules and controls. The comparison will retain the original estimates and change those choices explicitly.

1. Refit the filing-stage award model on its full 1985-2024 known-prior sample, then restrict decision years to 2010-2024 without changing its predictors.
2. Match the recent sample to the earlier 533-record estimation sample by EEI record ID. Check that awards, states and dates agree. Refit the filing design on those common records.
3. On the same common records, remove the during-case Treasury change while retaining the other stage controls. Then compare a specification using decision-date financial conditions and the prior known before filing.
4. Fit the earlier decision-date control set on those common records, first using the prior known before filing and then the original prior known before decision. Refit the original full sample as a numerical reference.

Every new model uses state and decision-year controls, equal row weights and state/decision-quarter clustered uncertainty. New intervals use the same t approximation as the filing study. The original paper table retains its previously reported normal-approximation intervals. These interval conventions do not alter the point estimates.

Changing controls and timing together is not a unique decomposition of the difference. Report the sample sizes, estimates and intervals, including comparisons with imprecise estimates. Do not select a specification to obtain a preferred result. Keep all original predictions and the original model tables unchanged.

The filing model includes both the Treasury yield near filing and its change before decision. Its filing-yield coefficient holds the subsequent change fixed, so it compares cases with higher yields at both endpoints. Its change coefficient holds the filing yield fixed. The older model has only a decision-date Treasury yield and a different set of financial controls. These coefficients therefore answer different conditional questions even on the same cases.

Inputs are the saved filing panel and original estimation table. They remain local reproduction inputs under the EEI data-rights policy. Publish aggregate estimates, model definitions and the reproduction script rather than case-level extracts.
