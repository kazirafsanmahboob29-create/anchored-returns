# Working paper

[Interest Rates and Authorized Equity Returns for US Electric Utilities](manuscript.md) is the main research paper for Anchored Returns.

[Download PDF](output/Mahboob_Utility_Returns_Working_Paper.pdf) · [Editable Word document](output/Mahboob_Utility_Returns_Working_Paper.docx) · [Read online](manuscript.md)

The paper follows one question through the analysis: how much information about a utility's next allowed return comes from financing conditions, earlier awards and the utility's own request? It explains the national results, tests the prediction rules on later cases, then uses original decisions to examine performance adjustments and capital structure.

The supporting [results index](../reports/README.md) links the tables and source records. Earlier specifications are preserved in the appendices and methods notes. The current paper, PDF and Word document are generated from the same manuscript.

## Build the paper

```sh
python -m pip install -e '.[paper]'
python paper/build.py
```

The Word file is written to `paper/output/`. Export it to PDF with Word or LibreOffice and inspect the resulting pages. The distributed PDF has been rendered and visually reviewed. To regenerate the two historical figures after rebuilding the national tables, run `python paper/figures.py`.
