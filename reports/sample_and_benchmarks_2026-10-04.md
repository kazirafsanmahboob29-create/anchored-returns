# Sample and historical benchmark review

Kazi Rafsan Mahboob · October 4, 2026

I reviewed five additional original Vermont orders and reconstructed H2 2019 national benchmarks from a complete original RRA decision table. The working library now contains 44 PDFs. The screened frame contains 32 candidate groupings: 22 eligible, nine excluded and one conditional settled substitute.

## Reviewed 15-order allocation

This is the current date-priority allocation from the screened records. It satisfies all numerical quotas: Connecticut 4, Massachusetts 4, Vermont 3, Maine 2, New Hampshire 1 and Rhode Island 1. Five decisions are dated 2019–2021 and ten are dated 2023 or later. Permanent P01–P15 IDs remain unassigned.

| Written date | State | Utility | Docket | Procedural classification |
|---|---|---|---|---|
| 2020-05-05 | RI | Narragansett Electric and Narragansett Gas | 4770/4780 | Conditional settlement substitute |
| 2020-10-30 | MA | NSTAR Gas | 19-120 | Contested ROE |
| 2021-09-30 | MA | Boston Gas | 20-120 | Contested ROE |
| 2021-10-15 | VT | Vermont Gas Systems | 21-0898-TF | Uncontested ROE on the record |
| 2021-10-18 | ME | Versant Power | 2020-00316 | Uncontested ROE on the record |
| 2023-10-23 | VT | Vermont Gas Systems | 23-0561-TF | Uncontested ROE on the record |
| 2024-06-28 | MA | Fitchburg Gas and Electric Light | 23-80 / 23-81 | Contested ROE |
| 2024-09-30 | MA | Massachusetts Electric and Nantucket Electric | 23-150 | Contested ROE |
| 2024-11-18 | CT | Connecticut Natural Gas | 23-11-02 | Contested ROE |
| 2024-11-18 | CT | Southern Connecticut Gas | 23-11-02 | Contested ROE |
| 2025-03-13 | ME | Versant Power | 2023-00336 | Contested ROE |
| 2025-07-25 | NH | Public Service Company of New Hampshire | DE 24-070 | Included by design |
| 2025-10-28 | CT | United Illuminating | 24-10-04 | Contested ROE |
| 2025-11-05 | CT | Yankee Gas | 24-12-01 | Contested ROE |
| 2026-08-28 | VT | Green Mountain Power | 25-1955-PET / 26-0096-TF | Contested ROE |

The new October 15, 2021 Vermont Gas Systems order replaces the older Northern Utilities decision under the existing date-priority rule. Its uncontested ROE was addressed in the rate-case record; this screening classification does not constitute a newly entered numeric award. The September 3, 2020 Vermont Gas order is also eligible, but the newer eligible records and quotas determine the current allocation. The 2024, 2025 and 2026 annual Vermont Gas formula implementations are excluded because they implement an existing formula.

The complete six-state written-decision census remains unfinished. The [screening log](../data/research/sample_screening.json) retains the unresolved New Hampshire and Maine originals and the Rhode Island 25-45-GE lead. The Rhode Island docket page, updated October 2, lists meeting and compliance records without a reasoned final-order link. I do not treat a meeting vote as the written decision required by the protocol. Rhode Island 4770/4780 remains a conditional settled substitute until the state search supports the absence of an eligible contested alternative.

I preserved the reviewed allocation with source fingerprints in [the dated proposal](../data/research/releases/2026-10-04-sample-review/proposed_sample.json). It is explicitly marked provisional. A public-document pilot would require a declared sampling amendment and would not support a claim that the selected records represent a complete eligible census. The [protocol](../docs/empirical_protocol_v0.1.3.md) has not been relaxed.

## H2 2019 reconstruction

The original January–December 2019 RRA report is attached to a public Kentucky commission filing. Its individual-decision Table 5 appears on PDF viewer pages 40 and 41. I retain all 126 electric and gas rows, including 47 rows without an authorized ROE. The table identifies rider cases with an LIR footnote.

Before selecting H2, the parser reconciles all four annual controls with original Tables 3 and 4: electric all-case n = 47, mean 9.65%; electric excluding riders n = 33, mean 9.64%; gas all-case n = 32, mean 9.71%; gas excluding riders n = 30, mean 9.72%. The report was published January 31, 2020, and Table 5 states that data were compiled January 29.

| H2 2019 series | Numeric non-rider decisions | Sum of reported ROEs | Calculated mean | Comparison value |
|---|---:|---:|---:|---:|
| Electric | 19 | 184.23 percentage points | 9.696315789...% | 9.70% |
| Gas | 23 | 224.25 percentage points | 9.75% | 9.75% |

These are calculated half-year means, not means printed by the publisher. Decimal arithmetic rounds half up to two percentage decimals for compatibility with the reported series. The raw result and included row IDs remain in the registry. This approach can create up to 0.5 basis point of rounding difference. No rounded annual average was subtracted from a first-half average.

The [original saved report](https://psc.ky.gov/pscecf/2020-00060/andrea.fackler%40lge-ku.com/08142020114603/2_-_KU_Responses_to_PSC_DR2_2020_ECR_Plan.pdf#page=40), [complete JSON evidence](../data/external/rra/rra_2019_decisions.json) and [raw decision table](../data/external/rra/rra_2019_decisions.csv) permit reproduction. Tests reject an omitted row, changed ROE, changed rider classification and an unsupported period. The research bundle also includes all 126 rows in CSV and Stata format.

## Remaining exact benchmark periods

The comparable registry contains ten service-period values across five half-years. Eight of the 15 proposed orders have every service matched, corresponding to nine of 17 service rows. The new matches are the joint Rhode Island decision and the proposed October 2021 Vermont Gas order. Rhode Island’s 2020 written report memorializes an earlier settlement. Its national comparison is indexed to that written date; it does not establish that the 2019 benchmark was available when the return was agreed. The dashboard and export retain the settlement role and timing limit.

| Missing half-year | Required services | Proposed orders affected | Evidence still needed |
|---|---|---|---|
| H1 2023 | Gas | Vermont Gas 23-0561 | Original rider-excluded half-year mean or complete original case table |
| H2 2023 | Electric, gas | Fitchburg 23-80 / 23-81 | Original H2 report or complete case-level data; the annual 2023 report does not provide the required reconstruction table |
| H2 2024 | Electric | Versant 2023-00336 | Original H2 report or complete case-level data; an annual mean is not a substitute |
| H1 2025 | Electric, gas | PSNH DE 24-070, UI 24-10-04, Yankee Gas 24-12-01 | Original rider-excluded means; public all-case summaries and witness workpapers do not establish the required scope |
| H1 2026 | Electric | GMP 25-1955-PET / 26-0096-TF | Confirmation of a comparable legacy-coverage mean or a documented bridge from the enhanced series |

The [publisher’s H1 2026 article](https://www.spglobal.com/market-intelligence/en/news-insights/research/2026/09/average-gas-roe-edges-down-as-electric-holds-firm-in-h1-2026) provides rider-excluded means but also describes expanded coverage. Those public values remain in the separate qualified reference registry. Its September 3 publication postdates the August 28 GMP order, so even a comparable value would be retrospective. The [publisher’s Wisconsin article](https://www.spglobal.com/market-intelligence/en/news-insights/research/wis-commission-staff-endorses-electric-gas-rate-increases-for-northern-states) provides H1 2025 all-case means and counts without the necessary rider-excluded breakdown.

I inspected Utah’s 25-057-06 public workpaper packages and additional Michigan and Kentucky filings. A citation to an RRA edition, a selected litigation subgroup or a witness risk-premium worksheet does not supply the complete original benchmark. Two Kentucky links return confidentiality-removal notices; cached search text is not used to reconstruct removed material. The [acquisition log](benchmark_acquisition_2026-10-04.json) records the source roles and reasons for withholding values. I have no licensed S&P/RRA access, and no correspondence or purchase has been initiated.

## Analysis and remaining research

The dashboard and analysis tables distinguish reconstructed and publisher-reported means. Figures use the current allocation, and the download contains executable R and Stata scripts, CSV/DTA datasets, figures and source fingerprints. R and Python execution can be checked locally; native Stata execution remains pending without a licensed runtime.

The numeric ledger remains at 55 verified facts and nine entered decisions; no new recommendations or awards were inferred from the screening review. The 67 coded units remain unchanged. Independent reliability remains unmeasured because no separate raters are available. Completing the sample census, obtaining the five compatible periods, entering the remaining verified case data and coding the selected full ROE sections are separate outstanding tasks.
