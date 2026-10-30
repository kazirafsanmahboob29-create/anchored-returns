# Anchored Returns

**Historical persistence and regional adjustment in authorized utility returns**

Kazi Rafsan Mahboob · Dartmouth College · 2026

[Current findings](reports/expanded-study/README.md) · [Methods](docs/expanded_study.md) · [Data sources](docs/expanded_sources.md) · [Reproduce](docs/REPRODUCIBILITY.md)

[![Research checks](https://github.com/kazirafsanmahboob29-create/anchored-returns/actions/workflows/checks.yml/badge.svg)](https://github.com/kazirafsanmahboob29-create/anchored-returns/actions/workflows/checks.yml)

## Research question

How much do financial conditions explain changes in the return on equity that utility regulators allow? How much information does the previous award provide?

I study **759 complete electric utility observations from 1995 to 2024**, covering 48 jurisdictions and 147 utility-state labels. I combine EEI rate-case records with Treasury yields, inflation, financial stress, state unemployment and case characteristics. A separate **1,141-observation** specification extends back to 1985 without the financial-stress variable, whose history starts later.

The original 533-observation study remains available. The extension preserves every original case ID in its common-period sample and increases the primary sample by **42.4%**. The [analysis plan](docs/expanded_analysis_plan_2026-10-28.md) records the specifications and identifies diagnostics added after the first estimates.

## Findings

**1. Earlier awards remain informative after utility and year controls.** A one-percentage-point higher prior award is associated with a **21.6-basis-point** higher current award, with an approximate 95% interval of **7.1 to 36.2**. The longer sample supports a positive within-utility association that was imprecise in the original window. Removing each jurisdiction in turn from the state/year model preserves a positive prior-award association.

**2. The estimated interest-rate relationship depends on the historical window.** With matched predictors and state/year effects, the Treasury coefficient is **-2.3 basis points** in 1995–2024 and **13.3 basis points** in 1985–2024 per one-percentage-point yield difference. This variation makes a single rate-response estimate difficult to generalize.

**3. Regional differences are suggestive, with less stable uncertainty.** The full-sample joint test of equal Treasury-change slopes rejects equality under state-only, quarter-only and two-way covariance. Individual region estimates remain imprecise, and some state-omission checks are less conclusive. The [regional results](reports/expanded-study/README.md#regional-differences-warrant-a-closer-investigation) report all intervals, denominators and omission checks, including one unavailable two-way joint test.

**4. A simple prediction rule is a demanding baseline.** Across **634 later-case predictions**, carrying forward the prior award gives **31.2 basis points** of mean absolute error, compared with **34.9** for the fuller model. The fuller model improves on the market-and-case model, but its extra complexity does not consistently improve on the previous award alone.

![Prediction errors across expanding training windows](reports/expanded-study/rolling-errors.png)

These are associations and retrospective prediction results. Authorized ROE is an allowed earnings opportunity, rather than a realized investor return. The study does not identify a causal effect of precedent. **One percentage point equals 100 basis points.**

## What the tools do

- **Build a source-linked panel.** Preserve workbook rows, actual prior-decision IDs, dated economic joins and inclusion flags.
- **Estimate comparable models.** Fit pooled, state/year, utility-state/year, award-change and regional specifications with clustered uncertainty.
- **Evaluate prediction across time.** Fit only earlier years and report every planned evaluation block, including blocks with insufficient history.
- **Inspect a region or period.** Recalculate a selected state/year model and export its real source rows without changing the published findings.
- **Check the calculations.** Compare NumPy with statsmodels and native R, verify input fingerprints and round-trip Stata datasets.

The indexed NumPy join matched direct calculations across all 759 cases within 1e-10. A [local benchmark](reports/expanded-study/join-benchmark.json) records its timing and scope.

## Run the analysis

Use Python 3.11 or later. Node.js 24 is needed for the browser test suite, and R is needed for native replication.

```sh
python3 -m venv .venv
. .venv/bin/activate
python -m pip install -e '.[test]'
python -m src.expanded_study --check
```

To rebuild the extension and independently check it in R:

```sh
python -m src.expanded_study
Rscript analysis/expanded.R reports/expanded-study
python -m src.expanded_study --verify-r
```

To investigate a selected region and period:

```sh
python -m src.expanded_study --explore levels --region Midwest --start 2010 --end 2024
python -m src.expanded_study --explore changes --region Northeast --start 2005 --end 2024 --export /tmp/northeast-changes.csv
```

Selections are labelled exploratory and return a specific reason when a model cannot be estimated. Exports retain the original source and prior-award IDs. See the [tool guide](docs/expanded_study.md#explore-a-region-or-period) for the definitions and controls.

The preserved numerical inputs are included and require no API key. A [separate retrieval command](docs/expanded_sources.md#retrieval-and-revisions) can download another economic vintage without replacing the published one.

## Project hierarchy

```text
anchored-returns/
├── src/
│   ├── economic_history.py    Indexed economic histories and dated joins
│   ├── panel_models.py        NumPy OLS, clustered covariance and contrasts
│   ├── panel_diagnostics.py   State omission checks
│   ├── expanded_study.py      Historical expansion, evaluation and explorer
│   ├── factor_study.py        Original 2010–2024 numerical study
│   ├── prediction_audit.py    Original fixed-prediction evaluation
│   └── research_*.py          Original-order evidence and coding tools
├── analysis/                  R and Stata replication scripts
├── data/external/             Preserved workbook and economic histories
├── data/research/             Order cohort, verified facts and coding records
├── reports/expanded-study/    Current tables, figures and manifests
├── reports/factor-study/      Original numerical release
├── presentation/              Local browser interface
├── wordpress/                 Portable browser application
├── tests/                     Numerical, source and application checks
├── docs/                      Methods, source definitions and reproduction
└── scripts/                   Acquisition, builds, benchmarks and checks
```

Start with [expanded_study.py](src/expanded_study.py), [expanded.R](analysis/expanded.R) and [expanded.do](analysis/expanded.do). The [architecture guide](docs/ARCHITECTURE.md) describes the other interfaces and publication components.

## Data coverage and validation

| Component | Coverage |
|---|---|
| Primary candidate table, 1995–2024 | 1,195 publisher observations; 899 observed awards |
| Main complete sample | 759 observations; 48 jurisdictions; 147 utility-state labels |
| Matched award-change analysis | 717 observations |
| Longer model without stress, 1985–2024 | 1,141 observations |
| Expanding-window prediction evaluation | 634 unique predictions in four available blocks |
| Economic inputs | 53 series, including unemployment histories for 49 jurisdictions |
| Original document cohort | 27 orders; 68 verified numeric facts |

The [methods](docs/expanded_study.md) explain missing values, timing rules and why these samples differ. Original document coding is separate from the numerical models. Independent coding agreement remains unmeasured, and five strict historical benchmark periods remain unresolved. Synthetic fixtures are confined to software tests.

Native R reconstructs the model designs and rolling predictions. Stata scripts and Unicode DTA datasets are supplied, with numeric round-trip checks; native Stata execution remains unverified. GitHub Actions checks documentation, Python, JavaScript and native R on pull requests and main-branch updates. The [validation record](docs/expanded_audit_2026-10-28.md) reports the checks completed for this release.

```sh
python -m scripts.check_links
python -m scripts.check_calculations
```

The [reproduction guide](docs/REPRODUCIBILITY.md) covers full source restoration, original PDF validation and the preserved browser interface. The [results index](reports/README.md) distinguishes the current extension from earlier releases. Input hashes, coding provenance and historical results remain available for inspection.

## Earlier article and browser workbench

The [published article](https://kazirafsanmahboob.host.dartmouth.edu/research/anchored-returns/) and [browser workbench](https://kazirafsanmahboob.host.dartmouth.edu/tools/anchored-returns/) present the original 2010–2024 study. The current historical extension and region explorer are available in this repository. Updating GitHub does not automatically update WordPress.

Run the preserved local browser application with `python -m src.research serve --snapshot`, then open http://127.0.0.1:8765/presentation/index.html. Original PDF viewing requires [source restoration](docs/REPRODUCIBILITY.md#restore-the-original-documents).
