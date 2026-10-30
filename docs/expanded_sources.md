# Sources for the historical expansion

Reviewed October 28, 2026.

The new [source manifest](../data/external/expanded_2026-10-28/manifest.json) records 53 series, 50,621 numeric source observations, retrieval times, URLs, file hashes and coverage. These are economic observations used as predictors, not additional utility cases.

## Case table

[EEI's finance page](https://www.eei.org/issues-and-policy/finance-and-tax) currently links its 2025 Q3 rate-review workbook as the newest public case file. The original [workbook](../data/external/eei/eei_rate_review_2025_q3.xlsx) remains unchanged. Its parser verifies the file hash, sheet identities, reporting cutoff and published quarterly checks before using the records. The expansion uses additional historical rows from this file. It does not infer new cases from press-release averages.

## Financial and labor-market histories

| Series | Producing source | Units and frequency | Treatment |
|---|---|---|---|
| [DGS10](https://fred.stlouisfed.org/series/DGS10) | Federal Reserve Board, H.15 | Percent; daily | Prior 90-day mean |
| [T10Y3M](https://fred.stlouisfed.org/series/T10Y3M) | Federal Reserve Bank of St. Louis | Percentage points; daily | Prior 90-day mean |
| [CPIAUCNS](https://fred.stlouisfed.org/series/CPIAUCNS) | U.S. Bureau of Labor Statistics | CPI-U index; monthly, not seasonally adjusted | Lagged 12-month inflation |
| [STLFSI4](https://fred.stlouisfed.org/data/STLFSI4) | Federal Reserve Bank of St. Louis | Index; weekly, ending Friday | Observation ending at least 14 days earlier |
| State unemployment, 49 jurisdictions | BLS, [Local Area Unemployment Statistics](https://www.bls.gov/lau/), distributed by FRED | Percent; monthly, seasonally adjusted | Two-month reference lag |

State identifiers combine the verified postal code with `UR`. For example, [CTUR](https://fred.stlouisfed.org/series/CTUR) and [CAUR](https://fred.stlouisfed.org/series/CAUR) identify seasonally adjusted unemployment rates for Connecticut and California. Each saved CSV must contain its exact expected series ID. The state mapping and per-series metadata retain all 49 identifiers and definition links. The direct BLS bulk endpoint returned HTTP 403 in this environment; the preserved histories were successfully retrieved through FRED's public CSV transport.

The request window is January 1980 through December 2024. A series begins later where its source history begins later. In particular, STLFSI4 starts in late 1993. The study therefore uses 1995–2024 for the full financial specification and a separately labelled 1985–2024 analysis without stress. No early stress values are imputed.

## Geography

State names, FIPS codes and postal abbreviations come from the [Census reference table](https://www2.census.gov/geo/docs/reference/state.txt). The four-region mapping follows the Census Bureau's [geographic definitions](https://www.census.gov/programs-surveys/economic-census/guidance-geographies/levels.html). The raw state table and derived [mapping](../data/external/expanded_2026-10-28/state_mapping.json) are preserved with hashes. The District of Columbia is treated as a state equivalent.

## Retrieval and revisions

```sh
python -m scripts.fetch_expanded_sources
python -m scripts.fetch_expanded_sources --output /tmp/separate-economic-vintage
```

The first command verifies an existing complete archive without downloading it again. A new output directory creates a separate retrieval. The script validates schemas, dates, numeric ranges and source identities, then publishes the directory only after all responses succeed. An incomplete request cannot become a completed snapshot.

A later retrieval may contain revisions. It is not interchangeable with the input vintage used in the published findings. The main build points to the preserved October 28 directory, while raw responses and metadata remain available for review. No API key or licensed data subscription is required for this retrieval.
