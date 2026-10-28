# National electric rate-case study

Kazi Rafsan Mahboob | October 21, 2026

I compare reported allowed ROEs in EEI's public rate-case workbook with Treasury yields on the authorization dates. The main comparison covers 2020–2021 and 2023–2024. It describes the source records; it does not identify a causal response to interest rates.

## Observations and exclusions

The original EEI workbook has 2,589 electric observations. Its reporting cutoff is September 30, 2025. I exclude 54 pending entries, three completed entries beyond that cutoff, and 302 completed rider or transmission entries. The remaining 2,230 base-rate observations contain 1,832 reported awards and 1,810 recorded request-award pairs. They cover 49 states plus the District of Columbia. Nebraska is absent.

An observation is a utility authorization entry, not necessarily a separate written order. Some entries share a cost-of-capital proceeding. The workbook's `Settled` status means completed; it is not a negotiated-settlement classification. Distribution and vertically integrated entries can include formula-related decisions. These categories do not isolate contested discretionary awards.

Missing awards are retained in the coverage denominator. They can reflect proceedings that did not reset the return. No zero, prior award, regional average or national mean is inserted in their place.

## Treasury matches

The preserved FRED DGS10 snapshot covers January 2010 onward. I match the latest nonmissing observation on or before the authorization date, withholding gaps above seven calendar days. All 166 observed awards in the main comparison have same-day matches. These current-vintage historical observations do not establish what information was available to a commission on its earlier decision date. Treasury yields measure nominal government-debt returns, and are not equity costs or investor returns.

The source workbook and Treasury files retain SHA-256 fingerprints. The workbook's counts and means reconcile with 31 published quarterly controls. These are source-consistency checks. They do not independently validate every underlying authorization or establish a complete national census.

## Main calculations

ROEs and yields are represented as integer basis points. Mean and median calculations retain full arithmetic precision; rounded percentages and basis-point changes are presentation values.

The main sample contains 77 observed awards in 2020–2021 and 89 in 2023–2024. Mean allowed ROEs change from 9.389610% to 9.712360%, a 32.274916 bp increase. Treasury yields at those same authorizations change from 1.227143% to 4.143708%, a 291.656501 bp increase.

The chart's default weighting is one value per matched authorization. Other settings retain only jurisdictions or utility-state groups observed in both periods. I compute a mean within each group and period, subtract the earlier mean from the later mean, and give each common group equal weight. Utility groups use the exact workbook label within the same state. Ownership changes and renamings have not been resolved.

- 32 common jurisdictions: allowed ROE change +23.350074 bp; Treasury change +286.864509 bp.
- 46 common utility-state groups: allowed ROE change +24.391304 bp; Treasury change +295.260870 bp.

2022 is omitted as the transition year, and 2025 is omitted from complete-year comparisons and annual figures. The interactive tool permits other nonoverlapping windows and warns when a selection includes the partial 2025 year. The table reports all filtered observations; the change chart uses only observations with both an award and a Treasury match.

## Interpretation

Case mix, capital structures, utility risk, regulatory mechanisms, filing lags and changing equity risk premiums can affect these comparisons. Repeated utilities and shared proceedings make independent-observation assumptions inappropriate. I report descriptive changes without causal coefficients or significance claims.

The New England cohort is a separate document study. Its records are not appended to the national table, which avoids counting a locally entered order twice. First-pass text codes and incomplete independent reliability do not support a quantitative explanation of the national pattern.

## Reproduce

```sh
./research national
Rscript analysis/national.R reports/national-study
python -m pytest tests/test_national_study.py -q
node --test tests/national/*.test.mjs
```

`reports/national-study/study.json` retains the source definitions, input fingerprints, aggregate calculations and every included source row. `cases.csv` and `annual.csv` have Unicode Stata counterparts. Native Stata code is supplied in `analysis/national.do`; it has not been executed in this environment.

CSV fields ending in `_bp` express percent measurements multiplied by 100. `award_bp=950` therefore means a 9.50% allowed ROE. A blank is missing. `source_row` refers to the original `All Rate Cases 2025Q3` worksheet. Exported JSON reports also retain the selection, source metadata and input fingerprints.

Source: [EEI finance publications](https://www.eei.org/issues-and-policy/finance-and-tax), [preserved EEI metadata](../data/external/eei/source.json), and [FRED DGS10](https://fred.stlouisfed.org/series/DGS10).

## New England comparisons

The regional panel retains the six New England states and the complete 2010–2024 years. It contains 57 completed base-rate publisher observations and 46 reported awards. The source includes formula and advice-letter implementations under its base-rate categories. These entries are not claimed as newly reviewed original PDFs.

`regional_panel.csv` contains every regional observation, including missing awards; `regional_states.csv` reports the 2010–2014 and 2020–2024 counts and means. Four of five states with awards in both windows have lower later means. Massachusetts rises by 6.25 basis points. Rhode Island has no reported award in the later window; Connecticut has one. No confidence intervals or jurisdiction-effect estimates are inferred from these counts.

In 2020–2021 versus 2023–2024, the region has seven awards per window. Their mean changes by +45.142857 basis points, while matched Treasury yields change by +291 basis points. Common-state weighting retains only Maine, Massachusetts and Vermont and gives +53.833333 and +284.166667 basis points. This is sensitive to the decision mechanism and case mix. These results do not establish a regional anchoring effect. The interactive geography selector also permits a comparison with observations outside New England.

A same-label check of the longer windows retains eight utility-state groups, with nine earlier and 15 later awards. Seven have lower later-period means. Equal weighting gives a 39.775-basis-point decline. The source labels are not independently resolved legal-entity histories, and the check does not hold regulatory mechanisms fixed.
