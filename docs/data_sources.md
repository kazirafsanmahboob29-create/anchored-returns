# Data sources

The main numerical study uses the preserved EEI rate-case table and dated economic series. The original-order study has its own documents, coding records and historical benchmark definitions. A source being accessible today does not establish that its present revision was available when a commission decided a case.

## Main study inputs

| Source | Included records | Role and access |
|---|---|---|
| [Edison Electric Institute Rate Review](https://www.eei.org/issues-and-policy/finance-and-tax) | 2025 Q3 workbook, 2,589 source rows | Public electric rate-case table. The complete-case estimation panel has 533 observations from 2010 to 2024. [Source metadata](../data/external/eei/source.json) and [reconstruction](eei_benchmarks.md). |
| [FRED DGS10](https://fred.stlouisfed.org/series/DGS10) | Preserved daily Treasury history | Lagged nominal ten-year Treasury yield. Public CSV transport; the documented JSON API requires a key. |
| [FRED T10Y3M](https://fred.stlouisfed.org/series/T10Y3M) | Preserved daily term spread | Ten-year minus three-month Treasury yield, in percentage points. |
| [FRED STLFSI4](https://fred.stlouisfed.org/series/STLFSI4) | Preserved weekly financial stress index | Financial conditions. Version 4 includes reconstructed earlier history. |
| [FRED CPIAUCNS](https://fred.stlouisfed.org/series/CPIAUCNS) and [BLS CPI](https://www.bls.gov/cpi/questions-and-answers.htm) | Preserved monthly CPI levels and separate BLS responses | Year-over-year inflation from index levels. The browser connector can request CPI through the BLS API. |
| [Federal Reserve H.15](https://www.federalreserve.gov/releases/h15/) and [Treasury XML](https://home.treasury.gov/treasury-daily-interest-rate-xml-feed) | Separate official Treasury retrievals | Source definitions and a second dissemination route for yield checks. |

The [October 26 source review](factor_source_review_2026-10-26.md) records definitions, retrieval dates, revision issues and redistribution restrictions. The [publication allowlist](../data/external/factor_research_2026-10-26/publication_allowlist.json) identifies the permitted economic inputs. Moody's histories reviewed locally are excluded from publication inputs. Source notices and required citations remain with the data.

The EEI workbook's bytes were rechecked on October 26 against its recorded SHA-256 hash. Its original publication date remains unverified. The empirical paper keeps that workbook and the saved economic vintage. Refreshing an API does not silently replace the paper's inputs.

## Original decisions and numerical evidence

The current document cohort contains 27 orders. The [cohort protocol](cohort_protocol_v0.1.5.md), [screening records](../data/research/sample_screening_v0.1.5.json) and [source catalog](../data/research/source_catalog.json) distinguish eligible orders, excluded records and supporting material. The cohort is a public-document study, not a completed census of all eligible six-state decisions.

The source library includes original commission PDFs, public docket attachments and publisher reports. The [restoration manifest](../data/source_files.json) records each source file's URL, relative path and SHA-256 fingerprint. Large original PDFs and review images are restored separately; they are not required to run the included browser snapshot. See [source restoration](REPRODUCIBILITY.md#restore-the-original-documents).

Applications, draft minutes and municipal debt-coverage decisions are not reclassified as final equity-return orders. Numeric facts retain their document, page, role and units. The three completed first coding passes are separate from the numerical panel; independent coding agreement remains unmeasured.

## Historical benchmarks

The [strict RRA registry](../data/external/rra_historical_benchmarks.json) contains ten service-period values across five half-years: H2 2019 and H1 2020, 2021, 2022 and 2024. Two values are complete-table reconstructions; eight are publisher-reported. The [reconstruction note](benchmark_reconstruction.md) and [126-row decision table](../data/external/rra/rra_2019_decisions.csv) document the H2 2019 calculation.

Five exact periods remain unresolved under the original same-service, rider-excluded definition: H1 2023, H2 2023, H2 2024, H1 2025 and H1 2026. The [October 4 acquisition record](../reports/benchmark_acquisition_2026-10-04.json) explains why all-case means, annual summaries and changed dataset coverage do not fill those fields. No licensed S&P/RRA connection is available.

The [context registry](../data/external/rra_context_sources.json) keeps other publisher reports separate. The [EEI half-year reconstruction](eei_benchmarks.md) supplies a broader retrospective electric comparison. It does not supply gas observations or silently replace a missing RRA benchmark.

## Refresh and access rules

- `./research refresh-treasury` preserves a new immutable FRED retrieval and its date matches.
- `./research verify-treasury` preserves the official XML responses and compares overlapping observations without overwriting either series.
- Browser Treasury and BLS refreshes recalculate a local scenario. They leave the published results fixed and include source dates in exports.
- An authenticated FRED JSON transport is optional. No key is needed for the included study or its CI checks.

Date matching never uses a future observation. It records the actual observation date and day gap. Missing values remain missing. Revision-sensitive historical research would require historical vintages in addition to observation-date lags.

The [link audit](link_audit_2026-10-27.md) records current website checks. Some commission, BLS and publisher pages reject automated requests. That response is reported as restricted access, not evidence that a page was read or that a new value was verified.
