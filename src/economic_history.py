"""Indexed, strictly dated economic joins for the historical case panel."""

import csv
import hashlib
import json
from dataclasses import dataclass
from datetime import date
from pathlib import Path

import numpy as np
import pandas as pd

from .factor_study import month_before

SOURCE = Path("data/external/expanded_2026-10-28")


@dataclass(frozen=True)
class SeriesIndex:
    dates: np.ndarray
    values: np.ndarray
    sums: np.ndarray

    @classmethod
    def from_records(cls, records):
        days = [r["date"] for r in records]
        if not days or days != sorted(set(days)):
            raise ValueError("Economic dates must be nonempty, sorted and unique")
        for day in days:
            if date.fromisoformat(day).isoformat() != day:
                raise ValueError("Economic dates must use ISO calendar dates")
        good = [r for r in records if r["value"] is not None]
        values = np.array([r["value"] for r in good], dtype=float)
        if not len(values) or not np.isfinite(values).all():
            raise ValueError("Economic observations must contain finite values")
        return cls(
            np.array([r["date"] for r in good], dtype="datetime64[D]"),
            values,
            np.r_[0.0, np.cumsum(values)],
        )

    @classmethod
    def from_csv(cls, path, series_id):
        with Path(path).open() as stream:
            reader = csv.DictReader(stream)
            if reader.fieldnames not in (["observation_date", series_id], ["DATE", series_id]):
                raise ValueError("Wrong economic series identity: " + series_id)
            records = [
                {
                    "date": r.get("observation_date", r.get("DATE")),
                    "value": None if r[series_id] in ("", ".") else float(r[series_id]),
                }
                for r in reader
            ]
        return cls.from_records(records)

    def windows(self, written, *, days=90, minimum=40, maximum_age=7):
        ends = np.asarray(written, dtype="datetime64[D]")
        if days < 1 or minimum < 1 or maximum_age < 0 or np.isnat(ends).any():
            raise ValueError("Invalid economic window")
        lo = self.dates.searchsorted(ends - np.timedelta64(days, "D"), side="left")
        hi = self.dates.searchsorted(ends, side="left")
        counts = hi - lo
        ages = (ends - self.dates[np.maximum(hi - 1, 0)]).astype(int)
        valid = (counts >= minimum) & (ages <= maximum_age) & (ages >= 1)
        means = np.full(len(ends), np.nan)
        means[valid] = (self.sums[hi[valid]] - self.sums[lo[valid]]) / counts[valid]
        return means, counts

    def latest(self, written, *, lag_days=14, maximum_age=14):
        cutoff = np.asarray(written, dtype="datetime64[D]") - np.timedelta64(lag_days, "D")
        if lag_days < 0 or maximum_age < 0 or np.isnat(cutoff).any():
            raise ValueError("Invalid economic cutoff")
        index = self.dates.searchsorted(cutoff, side="right") - 1
        chosen = np.maximum(index, 0)
        ages = (cutoff - self.dates[chosen]).astype(int)
        valid = (index >= 0) & (ages >= 0) & (ages <= maximum_age)
        values = np.where(valid, self.values[chosen], np.nan)
        observed = np.where(valid, self.dates[chosen].astype(str), "")
        return values, observed

    def exact(self, days):
        target = np.asarray(days, dtype="datetime64[D]")
        index = self.dates.searchsorted(target, side="left")
        safe = np.minimum(index, len(self.dates) - 1)
        valid = (index < len(self.dates)) & (self.dates[safe] == target)
        return np.where(valid, self.values[safe], np.nan)


class EconomicHistory:
    def __init__(self, root):
        self.folder = Path(root) / SOURCE
        self.manifest = json.loads((self.folder / "manifest.json").read_text())
        if self.manifest["schema"] != "anchored-returns-expanded-sources/1":
            raise ValueError("Unrecognized economic source manifest")
        for name, expected in self.manifest["files"].items():
            if hashlib.sha256((self.folder / name).read_bytes()).hexdigest() != expected:
                raise ValueError("Economic source fingerprint changed: " + name)
        self.series = {
            r["series_id"]: SeriesIndex.from_csv(self.folder / r["path"], r["series_id"])
            for r in self.manifest["series"]
        }
        mapping = json.loads((self.folder / "state_mapping.json").read_text())
        self.states = {r["state"]: r for r in mapping}
        if len(self.states) != len(mapping):
            raise ValueError("State mapping is ambiguous")

    def join(self, days, states):
        if len(days) != len(states):
            raise ValueError("Economic dates and states must align")
        days = list(days)
        months = [month_before(day, 2) for day in days]
        prior = [month_before(day, 14) for day in days]
        output = {}
        for series, key in (("DGS10", "treasury90"), ("T10Y3M", "curve90")):
            output[key], output[key + "_n"] = self.series[series].windows(days)
        now, previous = self.series["CPIAUCNS"].exact(months), self.series["CPIAUCNS"].exact(prior)
        output["inflation"] = np.where(
            (now > 0) & (previous > 0), 100 * (now / previous - 1), np.nan
        )
        output["inflation_month"] = months
        output["stress"], output["stress_date"] = self.series["STLFSI4"].latest(days)
        unemployment = np.full(len(days), np.nan)
        states = np.asarray(states)
        for state in sorted(set(states)):
            if state not in self.states:
                raise ValueError("State has no verified economic mapping: " + state)
            selected = np.flatnonzero(states == state)
            series = self.series[self.states[state]["series_id"]]
            unemployment[selected] = series.exact(np.asarray(months)[selected])
        output["unemployment"] = unemployment
        output["unemployment_month"] = months
        return pd.DataFrame(output)
