# Historical benchmark reconstruction

Kazi Rafsan Mahboob · October 4, 2026

This calculation note documents how I recover a missing half-year mean from a complete original publisher table. The frozen v0.1.3 sampling and coding protocol remains unchanged. The benchmark still uses the same service, excludes limited-issue riders and describes the most recent complete half-year before the written order.

I preserve every individual decision row, its service, written date, reported ROE, rider flag and native-text evidence. Rows without an ROE remain in the source table and do not enter the arithmetic mean. I exclude only the publisher's LIR-designated rider rows from this national comparison. The pilot's contested-case criteria do not change the national benchmark population.

Before calculating a half-year, I reconcile the complete extraction with the publisher's annual numeric counts and means, both with and without riders. I retain the included row IDs, sum and unrounded mean. Decimal arithmetic rounds half up to two percentage decimals to match the printed series; this introduces at most 0.5 basis point of rounding difference. I never subtract rounded annual and first-half means to infer a second-half mean.

The registry labels this method `case_level_reconstruction`. Its `printed_percent` remains null because the half-year mean is calculated rather than printed. The `display_percent` holds the rounded comparison value. Publisher-reported means retain their own method and original publication vintage. A report published after an order cannot be evidence available to that commission at the written date.

The implemented calculation uses the original January 31, 2020 edition's 2019 Table 5, with data compiled January 29. It checks the report identity, date, LIR definition, complete native extraction and four annual count/mean controls. The [review](../reports/sample_and_benchmarks_2026-10-04.md) reports the resulting H2 2019 means, source pages and remaining gaps. The [reproduction guide](../analysis/README.md) explains the complete CSV/DTA decision-table export.
