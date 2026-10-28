# Anchored Returns

**Kazi Rafsan Mahboob**

I investigate how authorized electric utility returns relate to market conditions and previous awards. The project combines a source-linked panel, regression and correlation tools, a temporal prediction check, and original New England regulatory orders.

[Read the paper](https://journeys.dartmouth.edu/kazirafsanmahboob29/?page_id=761) · [Run the models](https://journeys.dartmouth.edu/kazirafsanmahboob29/anchored-returns/) · [Inspect the evidence](https://journeys.dartmouth.edu/kazirafsanmahboob29/anchored-returns/#regional)

## Findings

The main panel contains 533 complete observations from 2010–2024, across 47 jurisdictions and 131 utility-state groups. The correlation between current and previous awards is 0.793. A positive pooled Treasury slope becomes close to zero after state and year controls. The prior-award association remains positive with those controls, but becomes less precise with utility-state effects.

A model fitted through 2019 has a mean absolute error of 23.3 basis points on 2020–2024 cases when it includes the previous award, compared with 53.1 for market and case variables alone. The previous-award baseline gives 24.2, so the augmented model improves on that stronger baseline by only 0.9 basis points. These are retrospective associations and prediction checks using revised historical data, not causal effects or real-time forecasts.

[Methods and robustness](docs/factor_study.md) · [Analysis specification](docs/factor_analysis_plan_v0.1.0.md) · [Source review](docs/factor_source_review_2026-10-26.md)

## Data

EEI's public 2025 Q3 workbook supplies 2,589 electric observations. After excluding pending entries, dates beyond the reporting cutoff, riders and transmission cases, the national study retains 2,230 completed base-rate observations. Of these, 1,832 report an award and 1,810 report both a request and an award. The source spans 1980 through September 2025. Recent comparisons use daily DGS10 observations from a preserved FRED retrieval.

The regional electric panel contains 57 completed EEI observations from 2010–2024, with 46 reported awards. In four of the five states with awards in both 2010–2014 and 2020–2024, the later-period mean is lower. A same-label check retains eight utility-state groups; seven have lower later means, with a 39.8-basis-point decline under equal weighting. These are comparisons of the recorded cases, not state policy estimates.

The original-document cohort contains 27 orders: 22 primary decisions, one settlement approval and four formula implementations. It contains 68 verified numeric facts and 22 entered returns. The four formula orders were already preserved in the source library and are now available as a separate analytical supplement. Complete first-pass text coding covers three orders and 67 units. Independent coding agreement remains unmeasured. The strict historical RRA series is incomplete; the separate EEI series retains its retrospective definition.

## Use the tools

The model workbench fits OLS with selectable controls, calculates Pearson and Spearman correlations, and exports source-linked calculation records. On WordPress, official Treasury XML and BLS CPI APIs refresh the yield, term spread and inflation measurements. Financial stress retains the explicitly dated paper vintage. Readers can export raw responses and their hashes. The case table and archived findings remain fixed.

The national comparison lets a reader change periods, regions, jurisdictions, case types and weighting, inspect source rows, share the selection and export records or a calculation report. The New England workspace supports individual order selections, source PDF pages, passage and fact searches, separate national benchmarks and saved selections. The Dartmouth edition also provides a blinded coding worksheet with local drafts and packet-compatible exports.

## Reproduce

Python 3.11 or later and Node.js 20 or later are used. R is optional; native Stata execution requires a licensed installation.

```sh
python3 -m venv .venv
. .venv/bin/activate
python -m pip install -e '.[test]'
./research national
./research factors
Rscript analysis/factors.R reports/factor-study
./research check
./research overview
./research serve
```

The prepared project folder includes preserved originals. After a Git clone, restore the separate source archive for full document validation and PDF reading. [Reproduction guide](docs/REPRODUCIBILITY.md) · [National study methods](docs/national_study.md) · [Data definitions](docs/DATA_DICTIONARY.md).

## Code layout

| Directory or module | Purpose |
|---|---|
| `src/factor_study.py` | Dated economic joins, panel regressions, clustered intervals and temporal evaluation |
| `presentation/factors/` | Independent browser QR regression, correlations and model workbench |
| `reports/factor-study/` | Complete panel, models, forecasts, figures and reproducible bundle |
| `src/national_study.py` | Source exclusions, Treasury matches, period comparisons and common-group checks |
| `presentation/national/` | National comparison interface and pure browser calculations |
| `presentation/workspace/` | New England order selection and calculations |
| `src/` | Document acquisition, extraction, validation, coding, benchmarks and reliability |
| `analysis/` | Native R and Stata scripts |
| `data/` | Preserved source metadata and versioned research inputs |
| `reports/national-study/` | National tables, calculation records, figure and study download |
| `tests/` | Evidence, calculation, import/export and source checks |
| `wordpress/` | Self-hosted application, page fragments, direct-source connectors and deployment manifest |
| `web/` | Hosted Worker, PDF reader and release builder in the prepared repository |

Source fingerprints, exact excerpts and recorded coding provenance are retained. Original documents and workbooks keep their publishers' rights. Cite the input fingerprints and cohort version with exported research results.

[WordPress deployment and update guide](docs/dartmouth_portfolio.md). The public application and downloads are hosted on Dartmouth.
