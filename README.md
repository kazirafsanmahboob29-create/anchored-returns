# Anchored Returns

**Interest rates, prior awards and authorized utility returns**

Kazi Rafsan Mahboob · Dartmouth College · 2026

[Research article](https://kazirafsanmahboob.host.dartmouth.edu/research/anchored-returns/) · [Interactive workbench](https://kazirafsanmahboob.host.dartmouth.edu/tools/anchored-returns/) · [Methods](docs/factor_study.md) · [Reproduce](docs/REPRODUCIBILITY.md)

[![Research checks](https://github.com/kazirafsanmahboob29-create/anchored-returns/actions/workflows/checks.yml/badge.svg)](https://github.com/kazirafsanmahboob29-create/anchored-returns/actions/workflows/checks.yml)

## Research question

When interest rates change, how much do utility regulators adjust the return on equity they allow? How closely does a new award follow the same utility's earlier award?

I examine these questions using **533 complete electric utility observations from 2010 to 2024**, covering 47 jurisdictions and 131 utility-state groups. I combine an EEI rate-case table with Treasury yields, inflation, financial stress and case characteristics. A separate collection of original orders supports document review.

An authorized return is the return on equity a commission allows a utility to earn through its rates. It is not a realized investor return. Throughout the analysis, **100 basis points equal one percentage point**.

## Main findings

**1. Earlier awards contain substantial information about new awards.** Current and previous awards have a correlation of **0.793**. After state and year controls, a one-percentage-point higher previous award is associated with a **26.7-basis-point** higher current award. Its 95% interval is 7.2 to 46.3 basis points.

**2. The interest-rate relationship changes with the specification.** In the pooled market-and-case model, a one-percentage-point higher Treasury yield is associated with a 15.8-basis-point higher allowed return. With state and year controls, that estimate is **-0.3 basis points**, with a 95% interval of -4.8 to 4.2. Year controls absorb much of the common movement in national rates. The pooled association therefore cannot be read as a stable rate-response estimate.

**3. A previous-award rule is a strong prediction baseline.** The model with a prior award predicts later cases much better than the market-and-case model. It improves only slightly on simply carrying forward the previous award: **23.3 versus 24.2 basis points** of mean absolute error.

![Current and previous authorized returns in the estimation sample](reports/factor-study/persistence.png)

These results establish persistence in the recorded awards. Possible explanations include stable utility risk, commission policy, formula design and reliance on precedent. The numerical models do not distinguish those explanations. With utility-state and year controls, the prior-award interval includes zero. The [full analysis](docs/factor_study.md) reports that specification and the sensitivity checks.

## Prediction comparison

I fit the models on 345 observations from 2010 to 2019 and evaluate them on 188 observations from 2020 to 2024. Mean absolute error is the average size of a prediction error, regardless of direction. Lower values indicate closer predictions.

| Prediction rule | Mean absolute error |
|---|---:|
| Training-period mean | 42.2 bp |
| Previous award | 24.2 bp |
| Market and case variables | 53.1 bp |
| Model including previous award | 23.3 bp |

The model improves on the previous-award rule by **0.9 basis points**. This is a retrospective evaluation using revised historical economic data. It is not a forecast produced in 2019 or a causal test of regulatory precedent.

## How the analysis works

1. **Build the panel.** Apply the case, year and completeness rules to the preserved EEI table.
2. **Construct dated variables.** Match strictly earlier awards and lagged economic observations without using same-day decisions as prior awards.
3. **Compare specifications.** Estimate pooled models, then add state/year and utility-state/year controls. Calculate uncertainty with clustering by state and authorization quarter.
4. **Evaluate and cross-check.** Compare later-case errors with simple baselines. Recompute selected estimates in R and check browser calculations against Python.

The [analysis plan](docs/factor_analysis_plan_v0.1.0.md), [data dictionary](docs/DATA_DICTIONARY.md) and [source guide](docs/data_sources.md) document the decisions behind these steps.

## Project hierarchy

```text
anchored-returns/
├── src/                    Python analysis, validation and command-line tools
│   ├── factor_study.py     Main panel, regressions and prediction checks
│   ├── national_study.py   National period comparisons
│   └── research_*.py       Original-order evidence, selection and coding tools
├── analysis/               R and Stata replication scripts
├── data/                   Preserved inputs and research records
│   ├── external/           EEI workbook, economic histories and source metadata
│   └── research/           Cohort, facts, coding records and dated protocols
├── reports/                Calculated results and figures
│   ├── factor-study/       Main estimation tables, R checks and figures
│   └── analysis/           Dated original-order analysis releases
├── presentation/           Local browser interface
├── tests/                  Statistical, source, connector and interface checks
├── docs/                   Methods, definitions and reproduction guides
├── scripts/                Build, source-restoration and link-check utilities
├── codebook/, project_docs/ Original coding definitions and workbook templates
├── wordpress/              Portable browser application
├── web/                    Optional service adapter and preserved export
└── portfolio/              Earlier publication fragments
```

Start with [src/factor_study.py](src/factor_study.py) for the main analysis, [analysis/factors.R](analysis/factors.R) for the R cross-check, and the [results index](reports/README.md) for saved outputs. The [architecture guide](docs/ARCHITECTURE.md) explains how the components connect. The current WordPress theme is maintained outside this repository.

## Run locally

Use Python 3.11 or later and Node.js 24.

```sh
python3 -m venv .venv
. .venv/bin/activate
python -m pip install -e '.[test]'
python -m src.research serve --snapshot --port 8765
```

Open **http://127.0.0.1:8765/presentation/index.html**. The included snapshot runs without API keys or original order PDFs. It supports model specifications, period comparisons, selections and calculation exports. Original PDF viewing and full document validation require [source restoration](docs/REPRODUCIBILITY.md#restore-the-original-documents).

On Windows, activate with `.venv\Scripts\activate` before running the same Python commands.

## Reproduce and check

```sh
python -m src.research national
python -m src.research factors
Rscript analysis/factors.R reports/factor-study
python -m scripts.check_links
python -m scripts.check_calculations
```

R independently checks 27 coefficient and clustered-standard-error pairs. Prepared Stata scripts are included; native Stata execution remains unverified. GitHub Actions runs the documentation and source-independent Python/JavaScript checks. See the [reproduction guide](docs/REPRODUCIBILITY.md) for complete evidence validation.

## Data coverage

| Component | Coverage | Purpose |
|---|---|---|
| EEI source table | 2,589 rows; 2,230 completed base-rate observations after exclusions | Starting table and national comparisons |
| Main estimation panel | 533 complete observations, 2010 to 2024 | Regressions and later-case evaluation |
| Regional numerical panel | 57 completed observations; 46 reported awards | New England comparisons |
| Original-document cohort | 27 orders; 68 verified numeric facts | Source review and close reading |
| Complete first coding passes | Three orders; 67 units | Initial passage analysis |

The main results use the numerical panel, not the passage codes. Independent coding agreement remains unmeasured, and five strict historical benchmark periods remain unresolved. No values or ratings are invented to fill those fields. Synthetic fixtures are confined to software tests.

The workbench can retrieve Treasury and BLS inputs for a separate calculation. Published findings retain their dated inputs. Original coding provenance, source hashes and historical releases remain available for inspection. See the [documentation index](docs/README.md), [source rights](docs/DATA_RIGHTS.md) and [citation record](CITATION.cff).
