# Check the pilot's financial arithmetic using base R.
# Run from the repository root after scripts.analyze_comparability.

financial <- read.csv("reports/comparability/pilot_financials.csv", na.strings = "")
sensitivity <- read.csv("reports/comparability/financial_sensitivity.csv", na.strings = "")

available <- complete.cases(financial[c("applied_roe", "approved_equity_share")])
calculated <- 100 * financial$applied_roe[available] * financial$approved_equity_share[available]
stopifnot(max(abs(calculated - financial$equity_allowance_per_100[available])) < 1e-10)

dollars <- with(sensitivity, rate_base_usd * equity_share * change_bp / 10000)
stopifnot(max(abs(dollars - sensitivity$annual_equity_component_change_usd)) < 1e-6)

stopifnot(nrow(financial) == 16L, length(unique(financial$proceeding_id)) == 15L)
cat("R arithmetic check passed:", sum(available), "financial schedules and",
    nrow(sensitivity), "sensitivity calculations.\n")
