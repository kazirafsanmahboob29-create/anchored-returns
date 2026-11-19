# Reproducing Anchored Returns

The current source package contains code, economic histories, aggregate results and original-order records. It excludes EEI's workbook, case-level extracts and compiled bundles. The [rights review](DATA_RIGHTS.md) explains the change. Earlier saved manifests describe the full local exports, not a claim that every input remains bundled in Git.

## Install and check the public source

Install Python 3.11 or later and [Node.js 24](https://nodejs.org/en/download). Both `python3` and `node` must be available in the terminal. The editable install includes PyMuPDF for the `pymupdf` and `fitz` imports. Base R is needed only for the `Rscript` commands.

```sh
python3 -m venv .venv
. .venv/bin/activate
python -m pip install -e '.[test]'
python -m scripts.check_public_release
python -m scripts.check_links
```

On Windows, activate with `.venv\Scripts\activate`. Public CI runs these source and software checks. Synthetic fixtures test calculations and timing rules; they never enter empirical results. This CI job does not independently reproduce the research estimates without the source data.

## Obtain the case data

Get the 2025 Q3 Rate Review workbook directly from [EEI](https://www.eei.org/issues-and-policy/finance-and-tax), subject to the provider's terms. The exact source URL and SHA-256 fingerprint are retained in [source.json](../data/external/eei/source.json). Import a user-obtained copy:

```sh
python -m scripts.import_eei /path/to/2025_Q3_Rate_Review_XLSX.xlsx
```

The script rejects a different version before writing the local source. No API key is needed for the public economic histories, but public availability does not establish permission to redistribute a provider's workbook. A different source vintage requires a separate analysis, not replacement under the recorded fingerprint.

For a use permitted by EEI's terms, `python -m scripts.import_eei --download` retrieves the recorded provider URL and performs the same fingerprint check. It does not grant redistribution rights.

## Rebuild the current studies

The original-order financial pilot can be rebuilt from the included fact records:

```sh
python -m scripts.analyze_comparability
Rscript analysis/comparability_check.R
```

This rewrites the pilot's figures, financial table and sensitivity calculations without acquiring the EEI workbook. To keep existing reports unchanged, run it in a disposable copy using the procedure below. The [pilot report](../reports/comparability/README.md) gives coverage and source locations.

For the national analyses, obtain the workbook as described above, then run:

```sh
python -m scripts.reproduce_filing --with-r
```

This rebuilds the national tables, earlier estimation inputs, historical panel, filing study and peer study in dependency order. Base R independently compares the current stage models and peer models with Python. The intermediate tables are generated locally and ignored by Git. The macroeconomic vintages remain fixed to the preserved histories. A new API retrieval is a separate input vintage.

For later reruns after the intermediate inputs exist:

```sh
python -m src.filing_study
Rscript analysis/filing.R reports/filing-study
python -m src.filing_study --verify-r
python -m src.peer_study
Rscript analysis/peer.R reports/peer-study
python -m scripts.compare_treasury_models
Rscript analysis/treasury_comparison.R
```

Native Stata has not been run. The earlier Stata scripts remain specifications for a licensed installation; their presence is not evidence of native replication. The peer extension has Python and native R comparisons.

## Build the paper

```sh
python -m pip install -e '.[paper]'
python paper/build.py
```

The maintained text is `paper/manuscript.md`; the build writes the editable Word document to `paper/output/`. Export it to PDF and inspect the pages. The distributed PDF and Word document use the same manuscript. Figures can be regenerated with `python paper/figures.py` after the national tables have been rebuilt.

## Use the local case explorer

After reproducing the data:

```sh
python -m http.server 8765 --bind 127.0.0.1
```

Open http://127.0.0.1:8765/presentation/filing.html. Filters select local cases and recalculate descriptive summaries; they do not refit the published models. A fresh checkout displays a source-acquisition message until the local tables are built. The earlier WordPress and service bundles are superseded build products and are excluded from the new package.

## Source-dependent and document checks

Run the full checks in a disposable copy because existing tests can rebuild publication files. From the repository root, with Node.js available:

```sh
(
    check_dir="$(mktemp -d)"
    trap 'rm -rf "$check_dir"' EXIT
    cp -R . "$check_dir/repo"
    cd "$check_dir/repo" || exit
    python3 -m venv "$check_dir/venv" || exit
    . "$check_dir/venv/bin/activate"
    python -m pip install -e '.[test]' || exit
    python -m scripts.check_calculations
    python -m pytest -q
)
```

To rebuild the financial pilot without changing existing reports, replace the two check commands with `python -m scripts.analyze_comparability`. The temporary copy and its environment are deleted when the subshell exits.

Additional document checks require the original sources:

```sh
python scripts/fetch_sources.py --check
python scripts/fetch_sources.py --download
python -m src.research check --full
```

### Limitations

I checked a clean clone with the declared Python dependencies and Node.js installed. `python -m scripts.check_public_release` and `python -m scripts.analyze_comparability` passed in a disposable copy. Both broader checks still failed on missing source inputs or generated files:

| Required material | Checks affected |
|---|---|
| Local EEI workbook and generated EEI exports | EEI and national-study tests in both checks |
| Generated factor, prediction, expanded-study and filing-study case tables | Saved-result tests in both checks |
| Legacy presentation entry page and compiled research files | Application, download and WordPress tests in both checks |
| Original order PDFs and the RRA source PDF | Additional document and reconstruction tests in the full pytest suite |

Node.js and PyMuPDF alone do not supply these files. The calculation command stops at its failed Python stage, so its later JavaScript stages were not verified. This clone has no source-dependent pytest skip mechanism; the missing-input tests fail rather than skip. Passing checks after restoring those materials remain NOT VERIFIED.

The existing EEI import command copies a workbook into the repository, and the national reproduction and filing-study calculation functions read that fixed location. I did not run them or copy the workbook. They need a separate path-handling decision before reproduction under an external-workbook-only rule.

The original PDF manifest contains source URLs and fingerprints. Restored documents must match those records. Independent ratings cannot be created by restoring files, and missing benchmark reports remain missing.

## Paper

The [manuscript](../paper/manuscript.md) is the canonical narrative. Earlier findings are indexed in [reports](../reports/README.md). The paper includes the peer extension, recent-block timing review, two verified original-order examples and an assistance acknowledgment. The earlier 533-case estimates are retained in an appendix. A [Treasury comparison](../reports/treasury-comparison/README.md) compares the earlier and filing-date designs over a common recent period and on matched cases. Independent passage-coding agreement remains unmeasured.
