# Methods and research records

Start with the [paper](../paper/manuscript.md) for the argument and the [results index](../reports/README.md) for its supporting exhibits.

## Current methods

| Guide | Purpose |
|---|---|
| [Reproduction](REPRODUCIBILITY.md) | Installation, data acquisition and the main build commands |
| [Project structure](ARCHITECTURE.md) | The code and data paths behind the current analyses |
| [Filing-stage methods](filing_study.md) | Requests, decisions, information timing and prediction |
| [Model guide](model_guide.md) | Plain-language explanations of controls, uncertainty and prediction error |
| [Comparison fields](comparability_fields.md) | Original-order measures, units, scope and evidence requirements |
| [Data dictionary](DATA_DICTIONARY.md) | Variables used across the project |
| [Source inventory](data_sources.md) | Data providers and access routes |
| [Source rights](DATA_RIGHTS.md) | Redistribution decisions and source acquisition |

## Dated analysis records

- [Filing-stage analysis plan](filing_analysis_plan_2026-10-30.md)
- [Research review and peer-extension plan](research_review_2026-10-30.md)
- [Treasury comparison plan](treasury_comparison_plan_2026-10-30.md)
- [Original-order comparison design](comparability_plan_2026-10-31.md)

These records preserve when questions, selection rules and follow-up analyses were specified. The October 31 pilot includes cases already examined during earlier work.

## Earlier methods and tools

[Historical expansion](expanded_study.md) · [Factor models](factor_study.md) · [Prediction audit](prediction_evaluation.md) · [National study](national_study.md) · [Regional collection](regional_expansion.md) · [Benchmark reconstruction](benchmark_reconstruction.md) · [Passage reliability](reliability_workflow.md)

The [workbench guide](USAGE.md) covers earlier evidence tools. The [publication guide](dartmouth_portfolio.md) records the optional website components. Historical sample targets and publication versions retain their original dates and definitions.

## Validation records

[Version 0.4.0](filing_audit_2026-10-30.md) · [Version 0.3.0](expanded_audit_2026-10-28.md) · [Version 0.2.2](audit_2026-10-28.md)

Run `python -m scripts.check_links` to check maintained Markdown paths and anchors. Add `--external` to request public links; restricted portals and missing pages are reported separately. The current source package is checked with `python -m scripts.check_public_release`.
