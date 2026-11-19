# Reproducing Anchored Returns

The current source package contains code, economic histories, aggregate results and original-order records. It excludes EEI's workbook, case-level extracts and compiled bundles. The [rights review](DATA_RIGHTS.md) explains the change. Earlier saved manifests describe the full local exports, not a claim that every input remains bundled in Git.

## Install and check the public source

Install Python 3.11 or later. The editable install includes PyMuPDF for the `pymupdf` and `fitz` imports. Base R is needed only for the `Rscript` commands.

```sh
python3 -m venv .venv
. .venv/bin/activate
python -m pip install -e '.[test]'
python -m scripts.check_public_release
python -m scripts.check_links
```

On Windows, activate with `.venv\Scripts\activate`. Synthetic fixtures test calculations and timing rules. They never enter empirical results. Workbook-dependent tests skip when their required local files are absent.

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
```

This rewrites the pilot's figures, financial table and sensitivity calculations without acquiring the EEI workbook. To keep existing reports unchanged, run it in a disposable copy as described under [Source-dependent checks](#source-dependent-checks). The [pilot report](../reports/comparability/README.md) gives coverage and source locations.

For the national analyses, obtain the workbook as described above, then run:

```sh
python -m scripts.reproduce_filing --with-r
```

This rebuilds the earlier factor estimation inputs, historical panel, filing study and peer study in dependency order. With `--with-r`, base R independently compares the filing and peer models with Python. The intermediate tables are generated locally and ignored by Git. The macroeconomic vintages remain fixed to the preserved histories. A new API retrieval is a separate input vintage.

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

The maintained text is `paper/manuscript.md`; the build writes the editable Word document to `paper/output/`. Export it to PDF and inspect the pages. The distributed PDF and Word document use the same manuscript. Figures can be regenerated with `python paper/figures.py` after the filing study has been rebuilt.

## Source-dependent checks

Use a disposable checkout if you want to preserve the saved outputs. In that checkout, install the test dependencies, import your workbook as above, run the local rebuild, and then run:

```sh
python -m pytest -q
```

The rebuild generates the local case tables needed by the saved-result tests. The decade test reads the local workbook. The [prediction evaluation](prediction_evaluation.md#reproduce) describes how to refresh the factor manifest for a local audit.

## Paper

The [manuscript](../paper/manuscript.md) is the canonical narrative. Earlier findings are indexed in [reports](../reports/README.md). The paper includes the peer extension, recent-block timing review, two verified original-order examples and an assistance acknowledgment. The earlier 533-case estimates are retained in an appendix. A [Treasury comparison](../reports/treasury-comparison/README.md) compares the earlier and filing-date designs over a common recent period and on matched cases. Independent passage-coding agreement remains unmeasured.
