# Original-order pilot records

October 31, 2026

These files add factual extraction to the unchanged Phase 1 roster. The [report](../../../../reports/comparability/README.md) presents the results and coverage.

| File | Unit and contents |
|---|---|
| `proceedings.json` | 15 proceedings; source links, dates, entities and disposition classes |
| `sources.json` | 17 original dispositions or related adopted documents, with retrieval metadata |
| `facts.json` | 165 entries, including 121 recorded values or context summaries and 44 explicit missing entries |
| `schedules.json` | 16 approved electric financial schedules, each linked to facts |
| `requests.json` | 15 main request records plus Niagara Mohawk's conditional multi-year alternative |

Rates and shares are decimals: 0.09 means 9%; 0.50 means 50%. Dollar values have been converted from the source's stated dollars, thousands or rounded millions. Original units and scope are explained in the evidence notes. Missing values remain JSON `null` with a reason.

PDF locations are one-based file page numbers, with printed pages or table names supplied where useful. DOCX paragraph and table locations are one-based counts from `python-docx`'s top-level `document.paragraphs` and `document.tables`; paragraph counts include blanks and exclude table cells. Do not count paragraphs in a PDF conversion or a word processor view and expect the same locator. Source identity and file fingerprints permit a reader to retrieve the matching original.

An order's description of a utility request is distinguished from inspection of the original filing. `initial_filing_document_inspected` remains false for this extraction, and the timing-audit class remains ambiguous. `stage_evidence_detail` distinguishes the source's initial-filing account, company schedules and other positions. The records do not certify that every request was available on the recorded application date.

Context summaries paraphrase the cited source with coding assistance. They are not independent human ratings. PECO's context entry identifies party positions within the adopted record. No number is inferred from a settlement's total revenue increase, and an absent performance adjustment is not coded as zero.

Source documents remain outside the distributable repository. `local_path` identifies a location relative to the separate restored research archive, not a file promised inside this source package. The [source register](sources.json) retains links and fingerprints. The original EEI workbook and case extracts are not used to generate these public financial tables.
