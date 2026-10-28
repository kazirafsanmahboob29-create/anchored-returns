# Anchored Returns

Kazi Rafsan Mahboob

## National extension

The national electric study compares reported allowed ROEs and Treasury yields at authorization dates. It uses 1,832 recorded awards from the public EEI table, with a recent-period comparison of 77 awards in 2020–2021 and 89 in 2023–2024. Mean awards rose by 32 basis points while matched Treasury yields rose by 292 basis points. Common-jurisdiction and utility-state comparisons retain the difference. These are descriptive results, with equity risk, timing and case mix left as possible explanations. [Methods and reproduction](national_study.md).

## Document research question

How do New England utility regulators use market evidence and regulatory precedent when explaining allowed returns on equity?

An allowed ROE is an administrative judgment informed by financial models, risk, legal standards and the record in a proceeding. Similar numerical awards can arise from different reasoning. I therefore record both the original figures and the written explanations behind them.

## Design

The fixed public-document cohort contains 27 original written decisions dated from 2019 through October 1, 2026. It includes all 22 eligible decisions in the screened library, one supplemental Rhode Island settlement and four formula-implementation orders. Both supplements are excluded from the default primary analysis. Formula-setting orders remain eligible for textual analysis even when no new numerical award is stated.

The cohort amendment replaces the earlier 15-order quota proposal for this release. That proposal is retained as a comparison. The expanded design is a bounded document cohort, not a random sample or a complete six-state census. Related utility-specific orders and shared plan proceedings retain explicit grouping identifiers.

## Measurements

I record company requests, operative original awards, performance adjustments, exact source passages, evidence categories and stance. Market evidence, other regulators' awards and the commission's own prior awards are distinct categories. Mentioning a category does not by itself demonstrate reliance. Party positions are separated from Commission analysis.

Numeric facts retain printed units, dates, viewer pages and exact excerpts. Passage records retain the original text and offsets. Source fingerprints identify the preserved documents. Complete first-pass coding covers three orders. Independent human agreement remains unmeasured.

National comparisons use the previous complete half-year and the same service. The original-report RRA series preserves rider exclusions and publication timing. A separate public EEI series reconstructs electric base-rate means from individual authorizations. EEI results remain retrospective and do not establish what a regulator knew at an earlier decision date. Treasury observations record the nominal interest-rate environment separately.

## Current contribution

The project supplies a reproducible way to connect regulatory text, numerical outcomes and comparison data. Its current records support descriptive comparisons, selection sensitivity checks and inspection of missingness. They do not identify a causal anchoring mechanism or an interest-rate pass-through effect.

The analysis workspace allows readers to select orders, change award weighting, inspect both national series, export records and preserve a complete analysis selection. The Python, R and Stata materials use common validated tables. Native Stata execution remains unverified.

[Cohort specification](cohort_protocol_v0.1.5.md) · [Data definitions](DATA_DICTIONARY.md) · [EEI reconstruction](eei_benchmarks.md) · [Reproduction](REPRODUCIBILITY.md)

## Regional panel

The EEI table supplies 57 completed electric observations in the six New England states from 2010–2024. Forty-six report an allowed return. Four of the five states with awards in both 2010–2014 and 2020–2024 have a lower later-period mean. Rhode Island has no later-period award and Connecticut has only one. This descriptive panel is separate from the original-order cohort and includes formula implementations. Its rows overlap with the document archive and must not be added together as unique orders.
