# Reproducing the empirical figures

I use one validated data export for R, Stata and Python. The export joins the preserved historical fact ledger with newer entries, without creating additional passage codes. It includes 20 decisions with numeric evidence, seven company request-award pairs and three completed first-pass sections. These entered decisions belong to the expanded 23-order document cohort. The original 15-order proposal remains a separate pilot specification.

## Generate the current release

From the project folder:

```sh
./research analyze
```

This command checks upstream evidence, exports CSV and Stata datasets, runs Python figures, runs an available `Rscript`, checks R's recomputed basis-point differences against Python and rebuilds the local site. Every run creates a new directory under `reports/analysis/`. The [latest pointer](../reports/analysis/latest.json) identifies the current manifest; its `output_path` is the release directory.

R uses base graphics and needs no additional packages. An installed R runtime can be selected with `--rscript /path/to/Rscript`. `--skip-r` produces Python outputs and datasets while recording that R was not executed. `--output /path/to/new-directory` creates a separate release without changing the current site or pointer. Existing release directories are preserved.

## Run Stata

No Stata installation was located on the research computer. I have prepared native graph code and Unicode `.dta` files for Stata 14.2 or later. Reading those files back through pandas checks the transfer of values, dates and missingness. It does not verify native Stata execution.

In a licensed Stata session, replace the two directory placeholders with the release's `data` folder and a new output folder:

```stata
do "analysis/figures.do" "RELEASE_DIRECTORY/data" "NEW_STATA_OUTPUT_DIRECTORY"
```

The do-file checks request-award arithmetic and coding denominators, then exports three PDF/PNG graphs and `checks.csv`. Compare that file with the release's `r/checks.csv` before reporting a three-software calculation check. Native Stata output is not included in the current manifest and must not be described as executed until the run has actually succeeded.

## Tables and measurement choices

| Table | Observation and meaning |
|---|---|
| `outcomes` | One entered decision. `request_pct` and `award_pct` are percentage points, such as 9.50. `gap_bp` is `(award_pct - request_pct) * 100`. An unentered request leaves the difference missing. |
| `coding` | One completed order and evidence category. Counts and percentages use that order's complete Commission-analysis units as the denominator, including units where the category is absent. |
| `commission_units` | One Commission-analysis unit and category. The 135 rows represent 45 units across three categories, not 135 independent passages. Page references and source hashes retain the coding trail. |
| `benchmarks` | One service and verified half-year from original RRA tables. Values exclude riders and retain the legacy dataset vintage and publication date. `estimation_method` separates publisher-reported means from H2 2019 complete-table reconstructions. |
| `benchmark_joins` | One proposed order and service. Joint orders retain separate electric and gas rows. Only the exact previous half-year can match; missing periods remain missing. |
| `treasury_daily` | One saved daily FRED observation from 2019 onward. Holidays and other absent values remain missing. |
| `treasury_orders` | One original written decision and its on-or-before Treasury match. `spread_bp` is a descriptive annual-rate difference, not an estimated equity risk premium. |
| `sources` | One reviewed source entry, its endpoint, saved path and fingerprint. XML years are separate acquisition entries, not independent providers or rate cases. |

Percent columns use percentage-point units; basis-point columns use hundredths of a percentage point. CSV dates use ISO format. DTA dates use Stata daily dates. `proposed` identifies membership in the current allocation; `final_sample` remains zero until selection is finalized. `award_kind` keeps an approved settlement separate from a commission-determined award. Operative performance-adjusted awards remain distinct from their unadjusted base values.

The figures use the original dated request and operative award fields. They do not substitute a witness recommendation, base return, later modification or inequality for a missing value. Rhode Island's May 2020 written report memorializes an earlier settlement, so its written date does not represent a new contested determination in 2020.

## Source and calculation checks

```sh
./research check
./research verify-treasury
```

The Treasury comparison downloads the official [XML feed](https://home.treasury.gov/treasury-daily-interest-rate-xml-feed) for the years needed by the matched decisions. Raw XML, parsed values and retrieval dates are preserved separately from FRED. The current comparison checks 1,440 overlapping dates and all nine decision-date observations, with no disagreements. It is a comparison of dissemination paths for nominal ten-year Treasury yields, not an independent measurement of coding reliability. After refreshing FRED, rerun `verify-treasury` before generating a new analysis release.

The source audit permits reviewed commission, publisher, university, issuer and government endpoints, checks every saved fingerprint and runs the existing evidence validators. It excludes the synthetic software demonstrations from empirical tables. This establishes traceability and calculation integrity; interpretation, final eligibility and independent coding agreement remain separate research questions.

The feeds currently end on different dates: FRED reports 5.24% for October 1, while Treasury reports 5.28% for October 2. The later Treasury value is preserved as separate source evidence; it is not inserted into DGS10. Only same-date overlap contributes to the 1,440-date comparison.

## Reading the figures

R generates a request-award comparison, case-specific coding shares and verified national comparison points. Python generates the exact benchmark coverage matrix and the Treasury-context figure. Stata code implements the same three graph subjects as R. No line connects missing benchmark periods, and no regression or significance claim is calculated from this incomplete set of decisions.

The complete first passes have unequal lengths: nine Commission-analysis units for New Hampshire, three for Versant and 33 for Green Mountain Power. A longer section should not receive the interpretation of more independent decisions. The recorded codes remain assisted first-pass interpretations with independent agreement unmeasured.

The current export also includes `request_gap_sensitivity`, `reliance_weighting` and `benchmark_comparisons`, in both CSV and DTA form. The first table removes one entered request-award pair at a time and recomputes the median; it does not estimate a confidence interval. The second retains pooled and equal-order reliance shares with their denominators. The third compares an entered original award with an exact half-year benchmark only if the report was published by the written decision. Missing periods and later publications remain unfilled. Approved settlements retain their award kind and timing note. Publication before a written report does not establish availability when an earlier settlement was agreed. Contextual annual and enhanced-dataset reports appear in the source inventory but do not enter the benchmark table.


## Reconstructed H2 2019 benchmarks

The release includes `benchmark_decisions.csv` and `.dta`: all 126 decisions from the original annual Table 5, including 47 rows without an ROE. The `limited_issue_rider` flag retains the publisher's LIR classification. `included_h2` identifies numeric, non-rider rows from July through December. Electric and gas rows yield 19 and 23 included observations and means of 9.70% and 9.75%, rounded half up to two decimal places. The JSON evidence file also retains exact native-text spans and the unrounded result.

The parser verifies the original report's publication date, data-compilation date and rider definition, and reconciles four annual count/mean controls before any half-year mean is accepted. A missing row, changed ROE or changed rider flag fails validation. Rounded annual and first-half means are never subtracted to derive H2. R, Python and prepared Stata figure notes identify the reconstructed period.
