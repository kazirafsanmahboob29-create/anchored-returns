# Fields for the rate-case comparison study

October 31, 2026

The [study design](comparability_plan_2026-10-31.md) defines the pilot and comparisons. Each extracted value is a fact record linked to a proceeding, utility-service unit and source. Dates use YYYY-MM-DD. Store rates as decimal fractions: 9.25% is 0.0925. A basis point is 0.0001 in stored rate units. Existing statistical models use percentage points, so convert stored rates by multiplying by 100 at that model boundary. Keep the conversion explicit.

## Record structure

| Record | Key | What one record represents |
|---|---|---|
| Proceeding | `proceeding_id` | One selected rate determination, including its related orders |
| Utility-service unit | `unit_id` | One legal utility, jurisdiction and separately identified service within a proceeding |
| Source | `source_id` | One identified document or locating record, with version and retrieval details |
| Fact | `fact_id` | One value or classification, with source location, date and role |
| Request version | `request_id` | One dated utility request, linked to the filing that contains it |
| Approved schedule | `schedule_id` | One approved rate-year or district schedule with consistent financial scope |
| Crosswalk | `crosswalk_id` | A reviewed link between an original proceeding and a local historical publisher row |

Proceeding and decision-group keys stay attached to every unit and schedule. Local publisher row identifiers and case-level extracts remain subject to the existing data-rights exclusions.

## Identity and chronology

| Field | Type | Entry rule |
|---|---|---|
| `decision_group_id` | Text | Shared by records from one joint determination |
| `legal_utility_name` | Text | Name at the time of the decision, exactly as identified in the record |
| `entity_id` | Text | Stable internal entity key, supported by an alias or merger record |
| `parent_name`, `ownership_as_of` | Text, date | Dated ownership context; preserve changes rather than applying today's parent to history |
| `state`, `docket` | Text | Preserve electric/gas docket distinctions in joint orders |
| `service` | Category | Electric distribution, integrated electric, gas, transmission, or unresolved |
| `proceeding_origin` | Category | Utility application, commission investigation or unresolved; retain the opening date separately |
| `initial_filing_date` | Date | Filed application date; notice of intent is a separate event |
| `request_filing_date` | Date | Date of the document containing this request version |
| `request_public_date` | Date | Confirmed public-availability date, if different or known |
| `decision_date` | Date | Original final disposition, with commission issue/adoption dates distinguished when necessary |
| `decision_public_date` | Date | Confirmed availability date for use as a historical comparator |
| `rates_effective_date` | Date | Economic effective date, which can precede the written order |
| `version_role` | Category | Original final, correction, reconsideration, appeal, remand, compliance or locating record |
| `legal_status_as_of`, `status_source_id` | Date, source key | Date and evidence for a legal-status check; unknown when no subsequent-history check exists |

## Requests and returns

| Field | Type or unit | Entry rule |
|---|---|---|
| `requested_roe` | Decimal rate | Utility position in the linked filing; retain every identified version |
| `request_stage` | Category | Initial, amended, rebuttal, settlement proposal or unresolved |
| `request_audit_class` | Category | Verified initial, verified revised, unchanged across verified versions, ambiguous or unmatched |
| `base_roe` | Decimal rate | Commission's explicit base return before separately stated adjustments |
| `adjustment_roe` | Signed decimal rate | Adopted increase is positive, reduction negative; never infer zero from silence |
| `adjustment_reason` | Text | Short factual description supported by the adopted decision |
| `applied_roe` | Decimal rate | Return used in the original approved disposition for this unit and schedule |
| `stated_reconciliation` | Category | Explicitly reconciled, differing scopes, unresolved conflict, or not stated |
| `derived_base_applied_difference` | Decimal rate | Applied minus base, calculated only when both are verified on the same basis; distinct from an explicitly stated adjustment |
| `value_role` | Category | Utility request, staff recommendation, other-party recommendation, commission adopted, scenario, historical reference or derived calculation |

Keep party recommendations and financial scenarios separate from adopted returns. A settlement without an explicit ROE receives a missing adopted value with the appropriate reason.

## Approved capital and rate base

| Field | Type or unit | Entry rule |
|---|---|---|
| `approved_equity_share` | Decimal share | Approved common-equity weight on the same basis as the applied return |
| `approved_debt_share`, `approved_debt_cost` | Decimal share, decimal rate | Record the components and weighting actually adopted |
| `approved_preferred_share`, `approved_preferred_cost` | Decimal share, decimal rate | Include when applicable; absence of evidence is distinct from an explicit zero share |
| `approved_total_return` | Decimal rate | Record the commission's adopted overall financing return if stated |
| `approved_rate_base_usd` | USD | Approved jurisdictional rate base, with stated original scale retained |
| `original_scale` | Category | Dollars, thousands of dollars or millions of dollars |
| `test_year_start`, `test_year_end` | Dates | Underlying test period |
| `rate_year_start`, `rate_year_end` | Dates | Schedule to which the approved financial inputs apply |
| `rate_base_basis` | Text | Average, year-end or other stated basis; service, district and included/excluded items |
| `tax_gross_up`, `tax_method` | Decimal factor, text | Only if supported by the approved revenue-requirement calculation |
| `scope_compatible` | Category | Confirmed, incompatible or unresolved across rate base, capital mix and return |

A requested rate base, consolidated parent balance sheet or unrelated FERC total is not an approved distribution rate base. Record an input's proposed/adopted role before using it. Calculation eligibility requires compatible scopes, units and rate years.

## Mechanisms and market conditions

| Field | Type | Entry rule |
|---|---|---|
| `disposition_class` | Category | Litigated, approved settlement, mixed or unresolved; explain mixed cases |
| `revenue_decoupling_status` | Category | Yes, no or unknown, with source and effective interval |
| `multi_year_plan_status` | Category | Yes, no or unknown, with plan dates |
| `capital_tracker_status` | Category | Yes, no or unknown, with mechanism name and covered investment |
| `earnings_sharing_status` | Category | Yes, no or unknown, with applicable threshold if verified |
| `mechanism_role` | Category | In force before filing, proposed at filing, adopted in this order, or unresolved |
| `treasury90` | Percentage points | Existing DGS10 90-calendar-day mean strictly before filing; retain observation count, last date and snapshot |
| `known_prior_date`, `known_prior_source_id` | Date, source key | Most recent compatible prior disposition known before filing, at most ten years old |

The pre-filing mechanism record and final-order mechanism record are separate facts. They can differ. A binary variable used in a later model must document how mixed or unknown categories were handled.

## Evidence attached to every central fact

Every entered fact carries `source_id`, `document_role`, `source_date`, `pdf_page` and `printed_page` where applicable, a short locator or passage, extraction date and verification status. For DOCX or HTML, use the section heading and paragraph or table locator instead of inventing a PDF page. The source record stores the original URL, source host, local fingerprint, version, retrieval date and access result.

Verification status is one of `pending`, `source_confirmed`, `conflicting`, or `derived`. A source-confirmed field requires inspection of the relevant context and adopted role. Automated search hits and a successful file download alone do not establish numerical verification. Preserve interpretive passage ratings separately from factual extraction.

## Missing values

Use null with one reason:

- `not_yet_reviewed`: extraction is pending.
- `document_unavailable`: the required source has not been obtained.
- `not_reported`: the inspected source does not disclose the value.
- `not_applicable`: the field does not apply, supported by the record.
- `ambiguous_scope`: the value exists but its entity, service or period is unclear.
- `conflicting_sources`: source versions disagree and resolution is pending.
- `unmatched_publisher_row`: the original proceeding cannot yet be linked to a historical record.

An explicit zero is a numeric value supported by evidence. It is never a missing-value code. Derived calculations remain missing if any required input is missing, conflicting or incompatible.

## First extraction checks

Check filing and decision chronology, request revisions, percentage conversions, document identity and adopted versus proposed roles. Where the order explicitly supplies all components, check base plus adjustment against applied ROE at the source's rounding precision. Check capital shares against the documented capitalization definition. Investigate discrepancies rather than forcing values to add up. Report coverage as proceedings, utility-service units and complete financial schedules separately.
