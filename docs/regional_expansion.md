# Regional evidence review

Kazi Rafsan Mahboob | October 21, 2026

## What changed

The regional quantitative analysis now includes a dedicated New England panel drawn from the preserved public EEI workbook. It contains 57 completed electric base-rate observations during 2010–2024, with 46 reported awards. Each observation retains its original worksheet row. The national tool can select New England, individual states or observations outside New England and can hold common states or utility-state labels fixed across periods.

The original-document cohort moves from 23 to 27 records by admitting four already preserved Vermont formula-implementation orders as a distinct supplement. The 22 primary decisions are unchanged. Two additional operative formula returns have been checked against the native PDF text and rendered pages: Vermont Gas 9.62% in 2025 and 9.63% in 2026. Those figures are not classified as new contested determinations. The 2024 filing has no separately entered numerical ROE; a later order's account of the prior return is not substituted for original evidence.

## Checks and limits

The five states with reported awards in both 2010–2014 and 2020–2024 show four decreases and one small increase. The underlying cases differ. Connecticut has one later-period award and Rhode Island has none. The chart and table therefore report award counts, completed-entry counts and missingness. No state policy effect or causal interest-rate response is estimated.

A formula can produce a changing return without a fresh discretionary determination. A performance adjustment can make an operative award lower than the financial base return. The original documents establish these mechanisms in individual cases. They do not establish how common each explanation is across all New England decisions.

New Hampshire original-order retrieval was attempted through public PUC and issuer records. The official Unitil DE 21-030 order 26,623 was identifiable, along with its later clarification, but the original PDF could not be retrieved: the direct request returned HTTP 403 and the browser URL returned a missing-file page. The SEC reproduction is a useful lead, not a locally preserved PDF. The old Massachusetts 18-150 API returned HTTP 503, and the previously cited CMP 2023 issuer PDF returned HTTP 404. None of these leads was counted as an acquired original. Remaining state-census searches are open.

The broader publisher panel is not a replacement for original-order review. It overlaps with the document archive. Its observations and the 27 document records must not be summed as a larger unique sample. It covers electric service only and uses the September 2025 workbook vintage. The document cohort includes gas decisions and later written dates through October 1, 2026. Neither source is described as a current, exhaustive six-state census.

## Reproduction

`./research national` rebuilds the publisher panel and executes the R figures when Rscript is available. `./research analyze` exports the validated document tables. `./research overview` rebuilds both interfaces and the original-order regional records. Python and browser tests compare the regional summaries and keep the three document strata separate. Native Stata code is supplied but has not been executed.

[Protocol](cohort_protocol_v0.1.5.md) · [National methods](national_study.md)
