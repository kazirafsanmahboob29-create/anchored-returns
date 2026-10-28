# Using Anchored Returns

The analysis workspace is the main entry point for comparisons. The evidence explorer provides the underlying passages, figures and original documents.

## Build a comparison

Choose the primary cohort, include the supplemental settlement, or load the original pilot proposal. Filter by state, utility service and written-date period. Check individual orders to change the analysis selection. The summaries use only the currently visible, checked rows. Select visible and Clear visible operate on the current filter results.

One value per order weights each observed award equally. One value per proceeding averages observed awards within each recorded proceeding group before summarizing across groups. Missing awards do not become zero. Request differences and national comparisons keep their own observed-pair denominators.

RRA comparisons require the preceding exact half-year, the same service, rider exclusion and publication by the written decision date. EEI comparisons are a separate retrospective electric base-rate reconstruction. No gas or 2026 value is inferred from that workbook.

## Preserve work

Save selection stores the current selection in the browser. Restore loads it again. Copy link preserves the order IDs, weighting and national series. Export selection CSV contains the selected records. Export analysis report adds the calculation summary, source references and input fingerprints. Import a selection accepts a matching JSON report and recalculates the results. These operations do not alter the cohort or original evidence.

## Inspect evidence and sources

Search the passage, numeric-fact or source-library tab. Filters and pagination update the displayed records. Each record links to its original endpoint and preserved PDF page. Exact excerpts, printed units, event dates and SHA-256 fingerprints remain available for review.

Refresh Treasury sources retrieves the connected public FRED and Treasury feeds. A completed retrieval is preserved with its raw source files. Historical research findings keep their fixed input vintage.

## Run the local tools

```sh
python -m src.research serve --snapshot
./research status
./research check
./research overview
./research analyze
```

The snapshot command starts the included release without original PDFs. The other evidence commands require restored sources. The local service prints its address. The optional Worker edition adds a PDF reader and stored market retrievals; those server features require a configured deployment. [Reproduction instructions](REPRODUCIBILITY.md) describe setup, source restoration, R and Stata materials and verification limits.

## Dartmouth portfolio

The current [portfolio](https://kazirafsanmahboob.host.dartmouth.edu/) presents the [research article](https://kazirafsanmahboob.host.dartmouth.edu/research/anchored-returns/). Its separate [workbench](https://kazirafsanmahboob.host.dartmouth.edu/tools/anchored-returns/) provides models, comparisons, the order library and a coding worksheet. The model tool can retrieve Treasury and BLS histories directly. Financial stress stays at the archived vintage. Exports include their source dates; the paper remains fixed. See [publication details](dartmouth_portfolio.md).
