# Version 0.3.0 validation

Checked October 28, 2026.

| Check | Result |
|---|---|
| Full Python suite with restored document evidence | 560 tests passed |
| Source-independent Python suite used by CI | 263 tests passed |
| JavaScript calculation and application suite | 28 tests passed |
| Original estimation IDs | All 533 preserved in the common-period portion of the extension |
| Economic inputs | 53 CSV identities, dates, values and source fingerprints validated |
| Native R models | 111 coefficient/SE/interval rows matched |
| Native R covariance sensitivity | 222 alternative-covariance rows matched |
| Native R joint tests and regional slopes | Six joint-test rows and four slope rows matched |
| Native R rolling predictions | 634 cases matched under each of four rules |
| Indexed economic joins | All 759 cases matched direct calculations within 1e-10 |
| Stata transfer | IDs and numeric model inputs preserved in CSV/DTA round-trip checks |
| Maintained Markdown paths and anchors | No missing targets |

The calculations use included real inputs and require no API key. R uses base packages. Python's NumPy coefficients and covariance are also tested against statsmodels. The source-acquisition failure test verifies that an interrupted retrieval cannot publish an incomplete snapshot. The region explorer tests verify filters, export identities and protection of published results.

The local date-join benchmark found a maximum absolute difference of 7.28e-13. It recorded about 0.589 seconds for direct calculations and 0.004 seconds for indexed calculations across the complete sample, excluding parsing. This is one local timing run, not a general performance guarantee.

Original EEI workbook bytes, the 2010–2024 study, its prediction audit and coding provenance remain unchanged. The original evidence archive passed its prior full audit, including 3,014 extracted PDF pages. The full suite in this release again includes the restored-source checks.

Some public endpoints restrict automated requests. Raw economic responses were successfully retrieved through FRED and preserved with their original producing-agency attribution. Restricted links are reported separately from missing pages. Native Stata execution remains unverified. Independent passage ratings and the five strict historical benchmark gaps remain separate from these numerical tests.

The [reproduction guide](REPRODUCIBILITY.md), [expanded methods](expanded_study.md), [source guide](expanded_sources.md) and [results](../reports/expanded-study/README.md) identify the commands, definitions and files behind these checks. GitHub Actions runs the numerical checks and native R replication on pull requests and main-branch updates.
