# Results and releases

## Main numerical study

[Factor-study methods](../docs/factor_study.md) explain the 533-observation estimation panel, specifications and later-case evaluation.

| File | Contents |
|---|---|
| [study.json](factor-study/study.json) | Model results, coverage and calculation metadata |
| [estimation.csv](factor-study/estimation.csv) | Complete-case estimation observations |
| [coefficients.csv](factor-study/coefficients.csv) | Estimates, uncertainty and specifications |
| [correlations.csv](factor-study/correlations.csv) | Pairwise association calculations |
| [holdout.csv](factor-study/holdout.csv) | Later-case prediction comparisons |
| [r-crosscheck.csv](factor-study/r-crosscheck.csv) | Native R coefficient and standard-error checks |
| [persistence.png](factor-study/persistence.png) | Current versus previous authorized return |
| [coefficients.png](factor-study/coefficients.png) | Estimates under alternative specifications |
| [artifact-manifest.json](factor-study/artifact-manifest.json) | Output fingerprints and packaging record |

## Original-order analysis

[analysis/latest.json](analysis/latest.json) points to the current document-analysis manifest. Its tables and figures have their own denominators. The document cohort and completed passage codes are not the national estimation panel.

The [October 4 sample and benchmark review](sample_and_benchmarks_2026-10-04.md) and [acquisition record](benchmark_acquisition_2026-10-04.json) are dated research records. Their sample counts describe that stage of work. Use the root [README](../README.md) and current manifests for present coverage.

Files under dated release directories are preserved calculation outputs. Reproduction writes a new release; presentation edits do not rewrite those records. See [reproduction instructions](../docs/REPRODUCIBILITY.md) for the distinction between source-independent checks and full document validation.
