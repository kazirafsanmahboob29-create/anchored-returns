# Public EEI half-year comparisons

I use the complete source table in EEI's public 2025 Q3 Rate Review workbook to reconstruct a separate historical electric series. The workbook is preserved with its original SHA-256 fingerprint. The parser retains 2,589 observations and reconciles the counts and means for 31 published quarters.

For each complete half-year, I select completed authorizations dated within that period, retain missing ROEs, and calculate the simple mean of observed ROEs in distribution and vertically integrated base-rate cases. Limited-issue riders and transmission cases are excluded. The workbook's `Settled` status identifies a completed entry; it is not used as a negotiated-settlement classification.

| Half-year | Observed base-rate ROEs | Sum of ROE percentages | Reconstructed mean |
|---|---|---|---|
| 2018 H2 | 19 | 181.35 | 9.54% |
| 2023 H1 | 12 | 115.70 | 9.64% |
| 2023 H2 | 36 | 347.88 | 9.66% |
| 2024 H2 | 27 | 265.32 | 9.83% |
| 2025 H1 | 18 | 174.23 | 9.68% |

The normalized observations preserve source worksheet row numbers. Reconstruction records retain exact sums, counts, missing rows, exclusions and unrounded means. Display means use two decimal places with half-up rounding. Workspace differences use those displayed means, consistent with the RRA display convention.

These observations provide retrospective electric context. I have not established the original workbook publication date or exact equivalence to each historical RRA report vintage. The series therefore does not fill the strict RRA registry, establish contemporaneous evidence, or supply gas comparisons. No complete H1 2026 electric period is available in this workbook.

The October 20, 2026 checks of both EEI finance-page routes found 2025 Q3 to be the newest linked Rate Review workbook. Newer assets for other financial subjects do not establish a newer rate-case table.

[Publisher finance page](https://www.eei.org/issues-and-policy/finance-and-tax) · [Preserved source metadata](../data/external/eei/source.json) · [Normalized observations](../data/external/eei/electric_observations.csv) · [Calculation records](../data/external/eei/reconstruction.json)
