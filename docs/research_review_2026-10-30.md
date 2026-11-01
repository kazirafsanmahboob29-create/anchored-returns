# Research review and next tests

October 30, 2026. This record follows an external critique and the existing results. It is not a preregistration. AI assistance contributed to the review, design and implementation; see the root acknowledgment.

## The question to return to

The motivating question is whether authorized utility returns respond mainly to market conditions or also track earlier awards and national peers. Data-center demand and grid investment motivated the author's interest. The existing study compares requests, decisions and prediction rules. It does not yet estimate a national peer-average association.

## What the critique changed

The README now leads with prediction performance and its reversal in the latest block. The market/prior model's error in that block is 37.45 basis points, versus 21.93 for the prior alone and 24.43 with the request. However, 40 of the 102 decisions predate 2022. The entire 2020–2022 filing cohort cannot be called a rate-shock test.

Year effects absorb annual national variation. Existing Treasury estimates therefore use within-year timing variation. The utility-state estimate also needs an explicit dynamic-panel warning. The coefficient-addition identity is a consequence of linear regression and belongs in the calculation notes, not among the substantive findings.

Public source copies and case-level extracts are being withdrawn from the current package after checking EEI's terms. Earlier Git history and hosted copies remain a separate task. No claims about new permission or completed historical removal are made.

## Peer-average analysis, specified before its first estimation

1. For each filing, construct trailing six- and twelve-calendar-month means of completed base-rate electric awards in **other states**, strictly before the filing date. Include awards with missing requests; exclude missing awards. Same-day decisions are excluded. Retain peer IDs and their latest decision date in local audit files.
2. The primary measure is the twelve-month mean with at least ten observed awards from at least five other states. Report coverage and missingness. Give each state/decision date total weight one before averaging to reduce the influence of multiple rows from one date. Report ordinary row weighting and six-month windows as sensitivities.
3. Regress authorized ROE on the own known prior, the peer mean, filing Treasury, inflation, state unemployment and distribution status, with state effects and no year effects. Use the existing 1985–2024 completeness and strict prior rules. Compare models on one common sample. Report state/authorization-quarter clustered uncertainty, peer-versus-own-prior collinearity and coverage by year.
4. Add a linear time trend, then authorization-year effects as separate sensitivity specifications. Report all three. The no-year-effects estimate can reflect common trends and omitted risks; it cannot establish that commissions consulted a peer average. A peer-window average is an observed reference measure, not documented commission knowledge.
5. For prediction, use the already defined filing blocks and decisions before their training cutoffs. Recompute peer features from strictly earlier awards, retain the full baseline design, and report unavailable blocks without dropping predictors. Compare peer addition against both the prior rule and market/prior model on identical cases. Do not select the window according to evaluation error.

These specifications were written after the earlier persistence and prediction results were known, but before calculating the new peer coefficients. Economic interpretation will follow the estimates, including null or contradictory results.

## Connect the numbers to orders

Rank the five largest absolute errors from the fixed model **with the request**, breaking ties by source ID. Retain the original prediction cutoff. Retrieve the corresponding final orders and verify utility, state, docket and decision date before reading passages. Do not substitute an easier case without recording why the original document is unavailable.

Apply the existing codebook to the ROE reasoning sections. Record citations to national allowed returns, own or jurisdictional precedent, gradualism, risk, capital access and investment requirements. Keep the commission's language distinct from parties' arguments. A large error is a case-selection rule for close reading, not evidence of anchoring by itself.

An independent human coder should rate five orders without seeing the first ratings. Until those ratings exist, report counts and disagreements only for available passes; leave independent agreement unmeasured. Another automated pass is not a substitute for human inter-rater reliability.

## One paper and a clear record

The [current findings](../reports/filing-study/README.md) are the canonical research narrative. Earlier numerical studies and portfolio articles are earlier versions, not separate completed papers. A six-to-eight-page working paper should combine the motivation, current numerical results, peer test and document evidence after those components are complete. Its abstract and conclusion must describe the results actually obtained.

## Assistance guidance checked

[Dartmouth SURFD's guidance](https://students.dartmouth.edu/surfd/guidelines-and-getting-started/policies/using-generative-ai) requires acknowledgment in materials submitted to SURFD and asks applicants to identify tools and uses, review the content and follow each program's rules. This is guidance for those submissions, not a determination that every research venue permits the same use. The repository acknowledgment covers design, sourcing, code, analysis and drafting rather than describing the assistance as proofreading.
