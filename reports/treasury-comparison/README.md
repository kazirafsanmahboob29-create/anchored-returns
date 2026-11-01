# Comparing the Treasury estimates

The long-period filing model and the earlier decision-date model give different Treasury associations. Restricting the filing model to the earlier period largely reconciles them. The two 2010-2024 samples each have 533 records, with 529 in common.

| Model and sample | Records | Basis points per one-point yield difference | 95% interval |
|---|---:|---:|---:|
| Filing design 1985-2024 | 1,135 | 21.20 | 12.67 to 29.73 |
| Same filing design 2010-2024 | 533 | 0.33 | -6.91 to 7.58 |
| Filing design on common cases | 529 | 0.30 | -6.95 to 7.55 |
| Earlier decision design on common cases | 529 | -0.04 | -4.49 to 4.40 |

All comparisons include state and decision-year controls. New intervals use the filing study's state/decision-quarter clustered t convention. The original table retains its normal-approximation intervals, so its interval endpoints differ slightly from a new refit even when the point estimate and standard error agree.

The [comparison plan](../../docs/treasury_comparison_plan_2026-10-30.md) was written after feedback on the paper. The full [eight-model table](treasury.csv) also changes the Treasury update, financial controls and prior timing on the common cases. These are sequential diagnostics; they do not assign a unique causal share to each specification choice. The original prediction exercise is unchanged.

After reproducing the local source-dependent inputs:

```sh
python -m scripts.compare_treasury_models
Rscript analysis/treasury_comparison.R
```

The base-R check reproduces all eight models and 62 coefficient rows, including uncertainty ranges, from the same prepared inputs. The saved CSVs contain aggregate estimates. The EEI case tables remain local reproduction inputs.
