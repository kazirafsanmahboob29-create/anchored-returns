# Project architecture

The project has three layers. Primary documents and dated external data form the evidence layer. Python modules validate and transform that evidence into a portable release. Browser and Worker modules provide the analysis interface and connected data service.

## Research modules

`research_ledger.py` checks source identity, exact page text and numeric roles. `research_sample.py` preserves the original quota design. `research_cohort.py` validates the expanded cohort against every eligible screening record, and `cohort_facts.py` validates additional numeric entries without rewriting the frozen first pass. Benchmark modules retain their own source definitions and calculation rules.

`research_overview.py` assembles the validated payload. `research_insights.py` calculates descriptive comparisons. `research_analysis.py` exports CSV and Stata tables and runs available Python and R figures. Existing output directories are immutable releases; `reports/analysis/latest.json` points to the current one.

## Browser modules

`presentation/workspace/analysis.mjs` contains pure selection, conversion, summary, import-validation and CSV functions. It has no DOM or network dependency. `index.mjs` binds those functions to the interface. The evidence explorer remains in `presentation/app.js`.

Saved selections use browser storage and can be exported as JSON. They do not alter the cohort or source records. An imported selection must match the cohort fingerprint, contain known unique order IDs and use a recognized weighting. Results are recalculated from the current evidence rather than accepted from an imported report.

## Hosted service

The prepared repository's `web/worker/` contains the request router, official market-feed parsers and PDF-reader routes. The service retrieves FRED CSV and Treasury XML over HTTPS. It writes complete retrieval objects before advancing the saved-snapshot pointer. Failed retrievals retain the last complete snapshot. Historical findings are never overwritten by a market refresh.

The build exports static evidence records and a small Worker entry point. Original PDFs are allowlisted by saved path and SHA-256. The PDF reader renders the original file in the browser. Hosting configuration contains no credentials, and runtime credentials are not included in the repository.
