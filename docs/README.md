# Documentation

## Start here

- [Reproduction](REPRODUCIBILITY.md): installation, the included snapshot, numerical rebuilds and source restoration.
- [Factor study](factor_study.md): the main panel, estimates, prediction comparison and limits of interpretation.
- [Prediction evaluation](prediction_evaluation.md): paired errors, uncertainty, annual stability and baseline comparisons.
- [Project hierarchy](ARCHITECTURE.md): the input, analysis, output and interface layers.
- [Data dictionary](DATA_DICTIONARY.md): variables, units and missing-value rules.
- [Source inventory](data_sources.md): data providers, original records and access status.
- [Using the workbench](USAGE.md): selections, models, evidence and exports.
- [Published files](../reports/README.md): results and dated release manifests.
- [October 28 audit](audit_2026-10-28.md): validation results, portability fixes and unresolved research checks.

## Research methods

- [Analysis specification](factor_analysis_plan_v0.1.0.md)
- [National electric study](national_study.md)
- [Regional expansion](regional_expansion.md)
- [Benchmark reconstruction](benchmark_reconstruction.md)
- [Reliability workflow](reliability_workflow.md)
- [Source rights](DATA_RIGHTS.md)

## Dated records

The empirical and cohort protocols describe decisions made at earlier stages of the project. They retain the original sample targets, coding provenance and date cutoffs. A historical target should not be read as the size or completion status of the current study. Use the root README and the corresponding report manifest for current coverage.

The [publication guide](dartmouth_portfolio.md) distinguishes the current Dartmouth portfolio from earlier Journeys page fragments. The portfolio theme is maintained outside this research repository. Some original documents still use their recorded Journeys media URLs.

## Check documentation links

Run `python -m scripts.check_links` from the repository root. It checks relative Markdown links, images and heading fragments in the maintained documentation. CI runs this check on pull requests and main-branch updates. Network checks are explicit: `python -m scripts.check_links --external --output /tmp/anchored-returns-links.json`. A blocked request is reported separately from a missing page. API examples and local server addresses are not public-page health checks. `--include-export` also inspects the copied documentation in the frozen service export; its historical paths are outside the maintained documentation check.
