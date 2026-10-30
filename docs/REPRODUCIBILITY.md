# Reproducing Anchored Returns

## Current request-and-decision study

Run `python -m src.filing_study --check` to verify fingerprints and recompute the results. To rebuild, run `python -m src.filing_study`, `Rscript analysis/filing.R reports/filing-study`, then `python -m src.filing_study --verify-r`. `make filing` performs the same sequence. The [methods](filing_study.md) explain sample construction and the case explorer at `http://127.0.0.1:8765/presentation/filing.html` after starting the snapshot server. Inputs are included and require no API key. `python -m scripts.fetch_filing_sources` verifies the supplemental Alabama archive or retrieves it if absent.

## Start with the included release

Python 3.11 or later and Node.js 24 are the supported setup. The calculation tests do not need an API key or original order PDFs.

```sh
python3 -m venv .venv
. .venv/bin/activate
python -m pip install -e '.[test]'
python -m src.research serve --snapshot --port 8765
```

Open http://127.0.0.1:8765/presentation/index.html. `--snapshot` serves the fingerprint-checked compiled release without rebuilding the document evidence. Tables, models and local comparison tools are available. A missing original PDF cannot be opened until it is restored. The portfolio also provides the published browser workbench at https://kazirafsanmahboob.host.dartmouth.edu/tools/anchored-returns/.

On Windows, activate with `.venv\Scripts\activate`. Run Python commands from the repository root. `requirements-lock.txt` records the original development environment; `pyproject.toml` declares the runtime dependencies.

## Rebuild the historical expansion

```sh
python -m src.expanded_study
Rscript analysis/expanded.R reports/expanded-study
python -m src.expanded_study --verify-r
python -m src.expanded_study --check
```

This is the current 759-observation extension. It also exports the separately defined 717-observation change panel, 1,141-observation longer-window sample, expanding-window predictions and region diagnostics. The [methods and explorer commands](expanded_study.md) describe sample definitions and interactive selections. All numerical inputs are included. The [source guide](expanded_sources.md) explains how to preserve another retrieval vintage without changing published inputs.

The local browser and WordPress bundle still present the original 2010–2024 study. The current extension is available through the repository reports and command-line explorer.

## Rebuild the original numerical study

```sh
python -m src.research national
python -m src.research factors
Rscript analysis/factors.R reports/factor-study
python -c "from src.factor_study import package; package()"
```

The first command reads the included EEI workbook and dated Treasury observations. The second constructs the economic panel and estimates the models. Base R independently recomputes 27 coefficient and clustered-standard-error pairs and draws the figures. The package command compares those values before recording artifact fingerprints. The same inputs should reproduce the reported counts and estimates, subject to normal floating-point differences.

Keep the fixed input vintage when reproducing the paper. A new API retrieval is a different run and should be saved separately. These historical series contain later revisions; observation-date lags do not reconstruct the information available to a commission in real time.

## Evaluate the saved predictions

```sh
python -m src.prediction_audit
Rscript analysis/prediction_audit.R reports/prediction-audit
python -m src.prediction_audit --verify-r
python -m src.prediction_audit --check
```

This separate extension checks the fixed later-case predictions without refitting models. It preserves the original study and writes paired errors, clustered intervals, annual and case-type tables, influence checks and figures under `reports/prediction-audit/`. The [method note](prediction_evaluation.md) describes the post hoc design and the 12 native R checks. `make prediction` runs the first three commands.

## Calculation and application checks

```sh
python -m scripts.check_calculations
```

This is the CI command. It runs the Python and JavaScript tests that do not require the original order PDFs, including statistical timing rules, source-independent case calculations, frozen-rating validation, HTTP access boundaries and import/export behavior. Synthetic test fixtures are software inputs only and never enter the empirical tables.

Native Stata syntax and Unicode DTA exports are included. Native Stata execution has not been verified. See [analysis/README.md](../analysis/README.md) and [factor_study.md](factor_study.md) for the cross-software checks.

## Restore the original documents

```sh
python scripts/fetch_sources.py --check
python scripts/fetch_sources.py --download
```

The source manifest lists recorded URLs and SHA-256 hashes. A download is accepted only when its bytes match the preserved source. Changed URLs, changed documents and blocked endpoints are reported as missing rather than silently substituted. Some review images have no public endpoint and can only be restored from the separate evidence archive.

If the separately preserved archive is available:

```sh
python scripts/fetch_sources.py --archive /path/to/anchored-returns-sources.zip
python -m src.research check
python -m src.research check --full
python -m pytest -q
```

The full suite checks PDF fingerprints, excerpts, rendered-evidence records and historical artifacts, so it is intentionally more demanding than CI. Original PDFs and review images are not part of the Git upload. Source restoration does not create independent ratings or resolve missing benchmark periods.

`check --full` also extracts every page in the empirical manifest again and compares its text with the saved extraction. Paths are resolved from the repository, so the check works from other working directories after installation. The older `check --legacy` option is reserved for the original development workspace. It requires the parent `Energy Research Project.zip`, early milestone reports and their locked environment; those are separate from the public source archive.

After restoring evidence, omit `--snapshot` to rebuild the document explorer when starting the local server.

## Optional browser service build

The `web/` directory contains the optional Worker adapter and a preserved release export. From that directory:

```sh
node scripts/build.mjs
node --test tests/*.test.mjs
node scripts/preview.mjs
```

The client and server build does not need hosting-account metadata. The host supplies its storage binding and deployment configuration. Original-source validation in `validate-release.mjs` requires the restored PDF files. Regenerating the release export requires the full document evidence and a checked analysis state.

## Publication source

`wordpress/` holds the portable research application bundle. `portfolio/` retains the previous publication fragments. The current Dartmouth WordPress theme is maintained outside this repository. Updating GitHub does not automatically publish changes to WordPress. See the [publication guide](dartmouth_portfolio.md).
