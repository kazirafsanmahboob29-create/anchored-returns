# Changelog

## 0.4.0 · October 30, 2026

- Compare 1,785 recorded request-and-award pairs and estimate stage models on 1,266 complete cases.
- Separate the prior-award association across requests and decisions on an identical 1,135-observation sample, with checked coefficient identities.
- Evaluate six rules on 568 later cases using strictly earlier training decisions and filing-stage prior awards.
- Add weighted inference, state omissions, independent R replication, prepared Stata syntax and source-linked exports.
- Add a cream-and-black case explorer with period, region and text filters, annual figures and CSV downloads.
- Preserve earlier studies, record request-vintage limitations and retain unavailable evaluation blocks.

## 0.3.0 · October 28, 2026

- Extended the primary estimation window to 1995–2024, increasing complete observations from 533 to 759. Added a separately defined 1,141-observation longer-window sample and 717 matched award changes.
- Preserved 53 economic series, including BLS unemployment rates for 49 jurisdictions, with source identities, retrieval dates and fingerprints.
- Added reusable NumPy date indexes, OLS, two-way clustered covariance, contrasts and state-omission diagnostics, tested against direct calculations and statsmodels.
- Added 15 comparable specifications, regional rate-change interactions and four available expanding-window evaluations with 634 predictions. Kept the insufficient-history block visible.
- Added a region/period command-line explorer, source-preserving CSV exports, Unicode Stata datasets and native R reconstruction of models and predictions.
- Added native Stata replication syntax without claiming licensed execution. Preserved the original study, prediction audit, source records and coding provenance.

## 0.2.2 · October 28, 2026

- Added a paired evaluation of the fixed 2020-2024 predictions, including clustered uncertainty, annual and case-type comparisons, weighting and influence checks.
- Added source-identity guards, artifact fingerprints and a native R cross-check of 12 prediction-evaluation quantities.
- Added a separate R job to continuous integration and a `make prediction` entry point.
- Expanded the README and results index with the new evidence.
- Fixed full evidence validation in a restored clone. Empirical paths now resolve from the project root; the original development audit is an explicit `--legacy` option.

The October 26 estimation sample, fitted models, original predictions and research records are unchanged. The prediction evaluation is a post hoc extension, not a new prospective forecast.

## 0.2.1 · October 27, 2026

- Added snapshot startup for a clone without the original PDF archive.
- Added one cross-platform command for the calculation and application checks used in CI.
- Reformatted Python modules and added comments on lag construction, clustered uncertainty and the temporal evaluation.
- Made reference-rater identity checks use the actual frozen reference rather than hard-coded product names.
- Removed the optional web build's dependency on a hosting-account metadata file.
- Replaced machine-specific paths in active document manifests with relative paths.
- Updated the README, reproduction guide and current portfolio links.

The national and factor studies were rebuilt after formatting. Sample coverage, regression estimates and holdout results are unchanged. Base R again matched 27 coefficient and clustered-standard-error pairs within 1e-7. Historical source and coding records retain their original bytes.

## 0.2.0 · October 26, 2026

The preserved numerical release includes the financial-factor panel, panel regressions, later-case prediction evaluation and native R cross-checks. The published article and its original download archives use this release.
