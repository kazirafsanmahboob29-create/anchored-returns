# Data definitions

## Observation units

A cohort member is an original written decision. The 23 members comprise 22 primary orders and one supplemental settlement. Connecticut's CNG and SCG decisions are separate documents in a shared proceeding group. Fitchburg's electric and gas determinations occupy one document with two service matches. Related Vermont plan and rate orders also retain shared proceeding groups.

`candidate_id` is a stable document identity. `proceeding_group` identifies known dependence; it is not a claim that different proceedings are statistically independent. `stratum` is `primary` or `settlement`. `status` retains the eligibility classification. `source_ids` identify preserved originals and supporting events. `source_sha256` freezes those source identities.

## Numeric evidence

ROE values are percentage points: `9.50` means 9.50 percent. A basis-point difference is `(award_percent - request_percent) * 100`. Settlement precision is retained, including 9.275 percent. A missing value is `null` in JSON and an empty cell in CSV; it is not zero.

A fact identifies its field, written-event date, source PDF, page, exact text and offsets. Awards from an original decision are separated from subsequent corrections and compliance events. Connecticut performance reductions are included when the award field explicitly records the adjusted return. Company requests are not inferred from witness recommendations, prior awards or later events.

`cohort_numeric_facts_v0.1.4.json` adds 11 awards. It supplements the earlier source-checked records and frozen coding ledger. Formula-setting orders can be eligible without containing a new numerical award.

## Analysis exports

`outcomes` contains entered decisions and their request-award roles. Its `proposed` and `final_sample` fields refer to the original v0.1.3 pilot design. Expanded cohort membership is defined by `cohort_v0.1.4.json`, separately from those legacy flags. The interactive workspace includes every cohort member, including orders without entered awards.

Award weighting can be one value per observed document or one mean per proceeding group. Request gaps remain observed document pairs. National comparisons use service rows, so a joint-service order may contribute two comparisons. Every summary reports its own denominator.

The 135 long-form coding rows represent 45 Commission-analysis units across three code categories. They are not 135 independent passages. Complete first-pass coding covers three orders. Independent human agreement has not been measured.

## National and market data

The strict RRA series requires a specific complete half-year, the same service, general rate cases excluding riders and a known publication vintage. A contemporaneous difference additionally requires publication by the written decision date. A later-vintage reconstruction is retrospective context.

Treasury yields are nominal annual rates. The source may omit holidays or other dates. Decision-date joins use the documented on-or-before observation rule. Current retrievals and historical research snapshots are separate datasets.
