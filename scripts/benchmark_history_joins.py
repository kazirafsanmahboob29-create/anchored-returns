"""Compare indexed joins with direct calculations on every complete case."""

import csv
import json
from time import perf_counter

import numpy as np
import pandas as pd

from src.economic_history import EconomicHistory
from src.expanded_study import ROOT
from src.factor_study import economic_join


def main():
    history = EconomicHistory(ROOT)
    frame = pd.read_csv(ROOT / "reports/expanded-study/estimation.csv")
    records = {}
    for series in ("DGS10", "T10Y3M", "CPIAUCNS", "STLFSI4"):
        with (history.folder / "macro" / (series + ".csv")).open() as stream:
            records[series] = [
                {
                    "date": r.get("observation_date", r.get("DATE")),
                    "value": None if r[series] in ("", ".") else float(r[series]),
                }
                for r in csv.DictReader(stream)
            ]
    start = perf_counter()
    direct = pd.DataFrame([economic_join(day, records) for day in frame.authorized_date])
    direct_seconds = perf_counter() - start
    start = perf_counter()
    indexed = history.join(frame.authorized_date, frame.state)
    indexed_seconds = perf_counter() - start
    columns = ["treasury90", "curve90", "inflation", "stress"]
    maximum = float(np.nanmax(np.abs(direct[columns].to_numpy() - indexed[columns].to_numpy())))
    if not np.allclose(direct[columns], indexed[columns], rtol=0, atol=1e-10, equal_nan=True):
        raise ValueError("Indexed economic joins differ from the direct calculations")
    print(
        json.dumps(
            {
                "cases": len(frame),
                "compared_variables": columns,
                "maximum_absolute_difference": maximum,
                "direct_seconds": direct_seconds,
                "indexed_seconds": indexed_seconds,
                "observed_speed_ratio": direct_seconds / indexed_seconds,
                "timing_scope": "One local run; parsing excluded. Indexed path also joins state unemployment.",
            },
            indent=2,
        )
    )


if __name__ == "__main__":
    main()
