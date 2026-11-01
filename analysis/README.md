# R checks and Stata specifications

Python builds the research inputs and estimates. The R scripts recalculate selected models and financial quantities from those inputs. The [reproduction guide](../docs/REPRODUCIBILITY.md) describes installation and data acquisition.

## Current analyses

| Analysis | Python entry point | R check |
|---|---|---|
| Requests and awards | `python -m src.filing_study` | `Rscript analysis/filing.R reports/filing-study` |
| Other-state peers | `python -m src.peer_study` | `Rscript analysis/peer.R reports/peer-study` |
| Treasury comparison | `python -m scripts.compare_treasury_models` | `Rscript analysis/treasury_comparison.R` |
| Original-order financial pilot | `python -m scripts.analyze_comparability` | `Rscript analysis/comparability_check.R` |

The national analyses require locally acquired case data. The financial pilot uses the original-order fact records included in this repository. The R checks use base R. Current figures are in the corresponding report folders; the paper's figures are rebuilt by `python paper/figures.py` after national reproduction.

## Earlier analyses

`expanded.R`, `factors.R` and `prediction_audit.R` support the earlier historical models and saved-prediction checks. Their commands and results are documented in the [results index](../reports/README.md) and [project map](../docs/ARCHITECTURE.md).

`figures.R` supports the original document-analysis exports. Those dated outputs are indexed by `reports/analysis/latest.json`; their denominators and source versions belong to that export.

## Stata

The `.do` files provide specifications for a licensed Stata installation. Native Stata execution has not been verified. Use the script-specific version declarations and input paths when running them. The current peer, Treasury and pilot comparisons have Python and native R checks.
