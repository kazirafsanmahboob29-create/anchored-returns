# Comparing authorized utility returns

Kazi Rafsan Mahboob | October 31, 2026 | Phase 1 study design

## The question

When a utility requests a return on equity, which earlier rate cases make useful comparisons? I will examine how the answer changes when I distinguish the financing allowance from performance adjustments, account for approved capital structure, and change the rules for selecting comparable cases.

This question follows from the historical study. The prior award is a useful predictor, and adding the recorded request improves average prediction accuracy. The next step is to investigate what those percentages represent. A commission can select a base return and then reduce it for service failures. It can also approve a different equity share. Both decisions affect the return allowance, but a table containing only one ROE cannot separate them.

The work will produce a comparison of actual proceedings, a sensitivity analysis of benchmark selection, and a financial calculation tied to an approved rate base. The historical analysis remains the foundation. The new document study supplies the institutional detail needed to interpret it.

## 1. Scope and selection

The development pilot contains **15 named proceedings** in Connecticut, Maine, Massachusetts, New Hampshire, New York and Pennsylvania. The decision window is January 1, 2015 through December 31, 2024. The focus is investor-owned electric distribution base-rate proceedings. These jurisdictions provide a manageable extension of the existing New England archive into neighboring electricity markets.

The [pilot roster](../data/research/comparability-v1/pilot.json) fixes the cases before the new fields are entered or new comparisons are calculated. Six proceedings reuse documents already examined in the project. Nine add named proceedings located through commission or utility records. Selection is purposive: it favors a feasible mix of utilities, years and decision processes. No claim of random or statewide coverage is attached to the pilot. Previously inspected cases and exposure during source searches are recorded in the roster.

The [screening register](../data/research/comparability-v1/screening.json) records every candidate considered for this phase: all 32 entries in the existing screening register, the earlier Massachusetts practice case, and the nine new proceedings. This is the complete bounded consideration list for Phase 1. It is not a census of six states. The old 27-document cohort retains its original definition.

### Admission rules

- The case concerns permanent electric distribution base rates within the decision window. Electric inputs in a joint electric/gas order must be separately identifiable.
- The disposition is a commission decision approving rates, including an approved settlement. A recommended decision, utility proposal or press release can locate a case but cannot establish its final numerical fields.
- Formula-only updates, temporary-rate orders, transmission-only cases, gas-only cases, municipal utilities and cooperatives are outside the pilot. A base-rate case that also establishes a multi-year plan remains eligible.
- The availability of a reported ROE is assessed after selection. An undisclosed settlement return stays in the roster and the coverage denominator. It is not reconstructed from a revenue increase or replaced with an easier case.
- Orders outside the window stay in the screening register. Already inspected later orders remain development material rather than a new test set.

The unit for selection is a **proceeding**, with a stable decision-group identifier. Source documents, utility-service records and rate-year schedules are linked underneath it. Joint decisions count once in proceeding totals. Separate legal utilities can have separate input records, with the shared decision group retained. A supplemental order does not create a second observation of the same determination. Merger and parent-company links require evidence before records are combined.

The primary outcome is the return authorized in the original final disposition. Corrections, reconsideration, appeals and later effective-rate changes receive separate dated records. This distinguishes a study of historical decisions from a statement about rates currently in force.

## 2. What to extract

The [field dictionary](comparability_fields.md) defines the records, units and evidence requirements. Extraction follows the same sequence for every selected proceeding:

1. Confirm the legal utility, electric service, docket, disposition and decision date.
2. Find the initial filing and each dated revision to the utility's requested ROE.
3. Record the commission's base return, any explicit adjustment, and the applied return.
4. Record approved equity share, debt and preferred-capital inputs, and the applicable rate base and rate year.
5. Record settlement status and the mechanisms actually described in the order.
6. Link each entered fact to its source, PDF page or document paragraph, and role in the decision.

Use the commission's own terminology. A recommended value and an adopted value have different roles. A missing adjustment is unknown until the order either states an adjustment or establishes the relationship between its base and applied return. Unknown values stay missing. A formula-derived difference can be calculated separately once its two inputs are verified.

## 3. Questions, measures and timing

| Investigation | Main comparison | Required inputs | Information cutoff | First output |
|---|---|---|---|---|
| Measurement | Base versus applied ROE | Explicit commission returns and adjustments | Original final disposition | Case-by-case reconciliation in basis points |
| Capital structure | ROE ranking versus equity-return allowance per dollar of rate base | Applied ROE and approved equity share on the same scope and rate-year basis | Original final disposition | Paired rankings and the cases whose order changes |
| Comparator choice | The same case against several dated reference groups | Prior awards, service type, Treasury conditions and mechanisms | Strictly before initial filing | Benchmark table with membership, coverage and sensitivity |
| Request timing | EEI request versus verified initial and revised requests | Dated filings and local publisher record | Initial filing for a filing-date prediction | Match classification and fixed-model sensitivity on matched cases |
| Financial stakes | A stated ROE difference applied to an approved capital base | Approved rate base, equity share and a stated return difference | One consistent approved rate year | Reproducible annual allowance calculation |

The pilot first establishes field availability and descriptive comparisons. Any later regression extension will have a separate dated specification after the pilot's coverage is understood. It will identify which observations have already been examined.

## 4. Fixed comparator rules

Two reference banks serve different purposes. The existing EEI history supplies broad numerical comparisons, retaining its recorded case classifications. The new order bank supplies verified base/applied returns and institutional details. Every output identifies its bank. The same proceeding appearing in both banks is linked and counted once within a comparison. Verified document attributes are not silently assigned to unmatched publisher rows.

The index date is the utility's **initial filing date**. The reference window includes its lower bound and excludes the filing day. A decision also needs a confirmed public-availability date before that cutoff. If only an order issue date is known, record it as a proxy and label the comparison retrospective. For commission-initiated investigations, record the proceeding's origin and locate any utility application separately. Do not substitute an investigation opening date for an unverified utility filing date. Such a case can remain in the completed-case comparison while its filing-date benchmark is unavailable.

| Rule | Membership | Minimum coverage | Summary |
|---|---|---|---|
| Own prior | Same verified legal utility, state and service; most recent available award before filing, no more than ten years old | One earlier decision group | Prior ROE, age and source |
| Recent distribution cases | Other-state distribution awards in the preceding 12 calendar months | Five distinct decision groups in at least three states | Mean, median, range and membership |
| Similar Treasury conditions | The recent distribution group, with the difference in pre-filing Treasury means no greater than 1.00 percentage point | Five decision groups in at least three states | Same summaries and the cases removed |
| Similar mechanisms | The Treasury-matched group, with the same revenue-decoupling status and multi-year-plan status as known before the index filing | Five decision groups in at least three states | Same summaries and field coverage |

Mechanism status for the index case comes from rules already in force before filing, not the plan subsequently granted in that case. A proposed new mechanism can be retained as a separate proposal field. Settlement versus litigated disposition can be shown as a separate completed-case stratification. The index case's eventual disposition cannot enter the filing-date match. Unknown status does not count as a match. The historical EEI bank lacks the document fields for the mechanism rule, so that rule uses only appropriately verified records.

These are initial feasibility rules for this new study. The older national peer test retains its own ten-award, five-state rule and its original results. It is not recalculated using this pilot's threshold.

Use the existing Treasury definition: the mean of available daily 10-year constant-maturity yields during the 90 calendar days strictly before filing, with at least 40 observations and a latest observation no more than seven days old. Retain the source snapshot, count and last date. A current revised history is labeled accordingly.

Within a reference bank, first average duplicate utility/service rows within a verified decision group. Then give each state/decision date one unit of weight before averaging. Report the number of decision groups and state/date groups separately. A joint schedule cannot receive extra weight just because it has several rate years.

Report the original group even if a narrower rule has insufficient coverage. An unavailable benchmark stays unavailable. The predeclared sensitivity checks use six- and 24-month windows, Treasury tolerances of 0.50 and 1.50 percentage points, ordinary decision-group weighting, exclusion of the index holding company's affiliates, and leave-one-state-out results. They are reported together rather than used to choose the most favorable result. Holding-company exclusions require verified, dated ownership links.

For each index case, report the benchmark change in basis points between rules, the authorized return's position in the reference distribution, and coverage. Compare base with base and applied with applied in the verified bank. Publisher headline returns retain their original meaning. Group-selection uncertainty will be shown through sensitivity tables; five groups are a reporting floor rather than an assurance of precision.

## 5. Request audit and prediction evaluation

Link a publisher row to an order only after checking utility, state, docket and disposition date. Assign one of five request classifications: verified initial, verified revised, unchanged across verified versions, ambiguous, or unmatched. A numerical match alone does not establish the filing date or request version. Use the source's displayed precision to distinguish rounding from a substantive revision.

The pilot sensitivity uses saved predictions and fixed fitted rules. Only a verified request input changes. Report matched-case counts, the signed prediction change and absolute error under both inputs. This measures the sensitivity of those cases to request timing. It does not replace the existing national evaluation.

A separate later temporal evaluation will reserve decisions after 2024 only after a candidate list, exposure log and model specification have been fixed. No pilot case is an untouched test observation. Final-order adjustments, approved capital structure and actual proceeding duration belong in explanations of completed cases. They are unavailable to a forecast at initial filing.

## 6. Financial calculation

For an approved rate base and capital structure on the same jurisdictional, service and rate-year basis:

**Annual equity-return allowance difference = approved rate base x approved equity share x ROE difference.**

ROE and equity share enter this formula as decimals. The comparison also reports the equity-return allowance per $100 of rate base, equal to 100 x equity share x applied ROE. This makes the role of capital structure visible before introducing utility size.

The first sourced example will show the original input pages, a 10-, 25- and 50-basis-point sensitivity table, and the calculation in dollars. Revenue-requirement calculations require documented tax treatment and any applicable adjustments. Total financing comparisons also require the relevant debt and preferred-capital components. Customer bill effects require class allocation and billing information.

## 7. Evidence and writing

The report will open with the question, the most informative comparison and its economic interpretation. Each exhibit should answer a named question. The main text will explain why the result matters and what evidence supports the proposed explanation. Technical definitions belong beside the first relevant measure, with longer methods in an appendix.

The five-largest-error reading remains a separate diagnostic exercise, using the original fixed ranking. Ordinary-error comparison cases will be selected by a recorded rule before their reasoning passages are read. The new pilot is not chosen by prediction error. Maine's already examined adjustment motivates the measurement question and is identified as prior knowledge in the roster.

Source-confirmed numbers, a commission's stated explanation, and the researcher's interpretation will be presented distinctly. A short limitations section at the end will cover sample selection, common policy trends, source timing, missing fields and unmeasured independent coding agreement. Assistance remains acknowledged in the repository's existing contribution statement.

## 8. Completion and amendments

Phase 1 is complete when the scope, unit, pilot roster, field definitions, comparison rules and information cutoffs are recorded and internally consistent. These files meet that design milestone. Phase 2 begins the full 15-proceeding extraction and request audit. Source-access status in the roster does not mean that the numerical fields are complete.

Retain every selected case in the coverage report. If source access or eligibility fails, record the reason before adding any replacement. Publish a dated amendment naming the original and replacement; do not overwrite this roster. Expansion toward 40-60 proceedings follows the pilot's coverage results and a new selection record.

### Limits of this design

This is a dated extension developed after the earlier findings and Maine example were known. It is not a preregistration of those results. The pilot is designed for measurement, comparison and feasibility. Historical associations and comparator distributions do not by themselves determine an economically appropriate ROE or identify a causal regulatory response. The broader study's original prediction targets remain unchanged.
