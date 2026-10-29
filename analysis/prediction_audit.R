# Recompute loss comparisons from the original predictions, including two-way covariance.
args <- commandArgs(trailingOnly = TRUE)
folder <- if (length(args)) args[1] else "reports/prediction-audit"
d <- read.csv(file.path(folder, "paired_predictions.csv"), stringsAsFactors = FALSE)
expected <- read.csv(file.path(folder, "python_checks.csv"), stringsAsFactors = FALSE)
models <- c("training_mean", "previous_award", "market_case", "with_prior")
stopifnot(!anyDuplicated(d$id), all(is.finite(as.matrix(d[c("actual", models)]))))
records <- list()
append_check <- function(name, value) {
  records[[length(records) + 1L]] <<- data.frame(check = name, value = value)
}
for (model in models) {
  error <- 100 * (d[[model]] - d$actual)
  append_check(paste0(model, ".mae_bp"), mean(abs(error)))
  append_check(paste0(model, ".rmse_bp"), sqrt(mean(error^2)))
}

for (reference in c("previous_award", "market_case")) {
  gain <- 100 * (abs(d[[reference]] - d$actual) - abs(d$with_prior - d$actual))
  n <- length(gain)
  residual <- gain - mean(gain)
  cluster_variance <- function(group) {
    scores <- tapply(residual, group, sum)
    g <- length(scores)
    stopifnot(g > 1)
    # The model has one intercept, so (n-1)/(n-k) equals one.
    (g / (g - 1)) * sum(scores^2) / n^2
  }
  variance <- cluster_variance(d$state) + cluster_variance(d$quarter) -
    cluster_variance(paste(d$state, d$quarter, sep = "|"))
  stopifnot(variance > 0)
  append_check(paste0(reference, ".improvement_bp"), mean(gain))
  append_check(paste0(reference, ".se_bp"), sqrt(variance))
}
checked <- do.call(rbind, records)
stopifnot(identical(checked$check, expected$check),
          max(abs(checked$value - expected$value)) < 1e-8)
write.csv(checked, file.path(folder, "r-crosscheck.csv"), row.names = FALSE)

years <- sort(unique(d$year))
values <- sapply(years, function(year) {
  z <- d[d$year == year, ]
  c(mean(abs(z$previous_award - z$actual)), mean(abs(z$with_prior - z$actual))) * 100
})
png(file.path(folder, "r-prediction-errors.png"), width = 1600, height = 1000, res = 180)
par(mar = c(5, 5, 3, 1), bty = "l", family = "sans", col.axis = "#272b29", col.lab = "#272b29")
barplot(values, beside = TRUE, names.arg = years, col = c("#a6aaa8", "#263d35"),
        border = NA, ylab = "Mean absolute error (basis points)", xlab = "Evaluation year",
        main = "Previous-award baseline and augmented model")
legend("topright", legend = c("Previous award", "Model with prior award"),
       fill = c("#a6aaa8", "#263d35"), border = NA, bty = "n", cex = .8)
mtext("188 preserved predictions. Models fitted on 2010-2019. Retrospective evaluation.",
      side = 1, line = 3.5, cex = .7)
dev.off()
cat(sprintf("R prediction audit passed: %d independently recomputed loss and uncertainty checks.\n", nrow(checked)))
