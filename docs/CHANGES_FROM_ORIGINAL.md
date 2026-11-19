# Changes from the original repository

The comparison covers files present in this repository under `src/`, `scripts/` and `tests/`, including files added here.

## Source code

- `src/expanded_study.py` removes the analysis-plan and join-benchmark files from its input fingerprints because those files were omitted.
- `src/factor_study.py` reads and validates the local workbook directly to remove the dependency on the national Treasury snapshot, fingerprints the inputs it uses, and drops ZIP packaging that included the workbook and case tables.
- `src/national_study.py` removes automatic ZIP creation because the archive included the EEI workbook and derived case tables.
- `src/peer_study.py` removes the research-review document from its input fingerprints because that document was omitted.

## Scripts

- `scripts/build_named_cases.py` was added to generate the five Section 5 schedules from retained public-order outputs and match them to saved local predictions.
- `scripts/check_links.py` clarifies that the optional service-export check applies when the export directory is present.
- `scripts/check_public_release.py` runs the restricted-file check and the retained pytest suite because the original check called browser and test files that were omitted.
- `scripts/check_restricted_files.py` was added to reject tracked paths in the withdrawal manifest and tracked DTA, ZIP and XLSX files.
- `scripts/reproduce_filing.py` drops the standalone national build and explorer instructions, and updates its help to describe the factor, historical, filing and peer rebuild that runs without the omitted national Treasury snapshot.

## Tests

- `tests/test_eei_benchmarks.py` removes the checks that require the original workbook or saved case exports so its two portable checks can run in a clean checkout.
- `tests/test_expanded_study.py` removes the saved Stata export and explorer checks and skips saved-sample and prediction checks when their local outputs are absent.
- `tests/test_factor_study.py` skips the archive-hash, join-date and holdout checks when the locally rebuilt factor study is absent.
- `tests/test_filing_study.py` removes the saved identity and Stata export test and skips case timing and prediction-sensitivity checks when local outputs are absent.
- `tests/test_prediction_audit.py` removes the saved-export fingerprint test and runs the saved-prediction comparison against a temporary local manifest so the original numerical assertions can run after a local rebuild.
- `tests/test_slim_fixtures.py` was added to check eligibility and prior-award rules, state omissions, and coding-sheet validation on invented data.

## Outputs verified in Phase C

- The rebuilt factor study matched the archived model estimates, sensitivity results, correlations, coverage and holdout results exactly, including prediction values and row order. The study JSON differed in its input fingerprints and three legacy Treasury context fields that became null.
- The filing rebuild exactly matched the saved sample counts, prediction error summaries and known-prior slopes checked in Phase C. There were 568 later cases. The pooled MAEs were 31.82, 33.58 and 26.79 basis points for the prior-only, financial-plus-prior and request models, respectively. The corresponding 2020–2022 filing MAEs were 21.93, 37.45 and 24.43 basis points. On the common 1,135-case sample, the request and award slopes were 22.24 and 17.13 basis points per percentage point of prior award. The displayed values are rounded.
- The checked peer estimates, uncertainty bounds, correlations and error summaries, the successive-change and Treasury comparison results in the appendices, and the original-order financial pilot figures traced to retained transcriptions matched their saved numerical values exactly.
- The 1985–2024 known-prior award fit matched the saved observation count, coefficients, standard errors and interval bounds exactly under all three covariance choices. Phase C checked the full sample only.
- Central Maine Power's error ranked third again. The predicted award was 9.357366%, compared with an applied award of 8.25%, for a signed error of +110.736608 basis points.
