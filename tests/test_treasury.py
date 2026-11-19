from datetime import datetime, timezone
import json

import pytest
import requests

from src.treasury import parse_csv, observations, match_date, refresh, load_snapshot


CSV = b"observation_date,DGS10\n2025-07-03,4.35\n2025-07-04,.\n2025-07-07,4.39\n"
NOW = datetime(2025, 7, 8, 12, tzinfo=timezone.utc)


def rows():
    return parse_csv(CSV, "2025-07-01", "2025-07-08")


def test_exact_decimal_and_missing_preserved():
    result = rows()
    assert result[0]["value_fraction"] == "0.0435"
    assert result[1]["value_fraction"] is None
    assert len(result) == 3


@pytest.mark.parametrize(
    "content",
    [
        b"<html>denied</html>",
        b"DATE,DGS10\n2025-07-03,4.35",
        b"observation_date,DGS10\n2025-07-03,4.35,extra",
        b"observation_date,DGS10\n2025-07-03",
    ],
)
def test_reject_bad_schema_and_html(content):
    with pytest.raises(ValueError):
        parse_csv(content, "2025-07-01", "2025-07-08")


@pytest.mark.parametrize("value", ["NaN", "Infinity", "4,35", "bad", "35"])
def test_reject_invalid_numeric_values(value):
    with pytest.raises(ValueError):
        observations([("2025-07-03", value)], "2025-07-01", "2025-07-08")


@pytest.mark.parametrize(
    "days", [["2025-07-03", "2025-07-03"], ["2025-07-07", "2025-07-03"], ["2025-07-09"]]
)
def test_reject_duplicate_unsorted_and_future_observations(days):
    with pytest.raises(ValueError):
        observations([(day, "4.35") for day in days], "2025-07-01", "2025-07-08")


def test_holiday_and_weekend_use_earlier_not_future():
    for target, gap in [("2025-07-04", 1), ("2025-07-06", 3)]:
        match = match_date(rows(), target)
        assert match["observation_date"] == "2025-07-03"
        assert match["value_fraction"] == "0.0435"
        assert match["gap_days"] == gap
    assert match_date(rows(), "2025-07-07")["observation_date"] == "2025-07-07"


def test_trailing_weekend_inside_requested_period_and_stale():
    match = match_date(rows(), "2025-07-08", coverage_end="2025-07-08")
    assert match["gap_days"] == 1 and match["status"] == "matched"
    stale = match_date(rows(), "2025-07-15", coverage_end="2025-07-15")
    assert stale["status"] == "stale_requires_review"
    assert stale["value_fraction"] is None and stale["observed_fraction"] == "0.0439"


def test_outside_coverage_and_no_nonmissing_prior():
    assert match_date(rows(), "2009-01-01")["status"] == "outside_observation_coverage"
    assert match_date(rows(), "2025-07-08")["status"] == "outside_observation_coverage"
    data = observations([("2025-07-03", "."), ("2025-07-07", "4.39")], "2025-07-01", "2025-07-08")
    assert match_date(data, "2025-07-04")["status"] == "no_prior_nonmissing_observation"


class Response:
    content = CSV

    def raise_for_status(self):
        pass


class Session:
    def get(self, url, **kwargs):
        self.url, self.kwargs = url, kwargs
        return Response()


def test_snapshot_round_trip_and_tamper(tmp_path):
    session = Session()
    meta = refresh(tmp_path, start="2025-07-01", end="2025-07-08", now=NOW, session=session)
    assert meta["transport"] == "csv" and meta["missing"] == 1
    assert session.kwargs["timeout"] == (10, 30)
    assert load_snapshot(tmp_path)[1] == rows()
    (tmp_path / meta["observations_path"]).write_text("[]")
    with pytest.raises(ValueError, match="changed"):
        load_snapshot(tmp_path)


def test_failed_download_cannot_replace_existing_snapshot(tmp_path):
    refresh(tmp_path, start="2025-07-01", end="2025-07-08", now=NOW, session=Session())
    pointer = (tmp_path / "data/external/treasury/latest.json").read_bytes()

    class Failed:
        def get(self, *args, **kwargs):
            raise requests.HTTPError("credential-bearing-url")

    with pytest.raises(ValueError) as error:
        refresh(tmp_path, now=NOW, session=Failed())
    assert "credential" not in str(error.value)
    assert (tmp_path / "data/external/treasury/latest.json").read_bytes() == pointer


def test_api_requires_key_and_never_saves_it(tmp_path, monkeypatch):
    monkeypatch.delenv("FRED_API_KEY", raising=False)
    with pytest.raises(ValueError, match="FRED_API_KEY"):
        refresh(tmp_path, now=NOW, transport="api", session=Session())
    monkeypatch.setenv("FRED_API_KEY", "private-key-placeholder")

    class ApiSession:
        def get(self, *args, **kwargs):
            response = Response()
            response.content = json.dumps(
                dict(
                    units="lin",
                    order_by="observation_date",
                    count=1,
                    observations=[dict(date="2025-07-03", value="4.35")],
                )
            ).encode()
            return response

    meta = refresh(tmp_path, now=NOW, transport="api", session=ApiSession())
    assert "private-key-placeholder" not in json.dumps(meta)
    assert load_snapshot(tmp_path)[1][0]["value_fraction"] == "0.0435"


def test_future_request_fails_before_network(tmp_path):
    with pytest.raises(ValueError, match="future"):
        refresh(tmp_path, end="2025-07-09", now=NOW, session=Session())


@pytest.mark.parametrize(
    "field,value",
    [
        ("first_observation", "2025-07-02"),
        ("last_observation", "2025-07-08"),
        (
            "latest_nonmissing",
            {"date": "2025-07-07", "printed_percent": "5.00", "value_fraction": "0.05"},
        ),
    ],
)
def test_rehashed_metadata_cannot_misstate_latest_yield_or_coverage(tmp_path, field, value):
    from src.research_ledger import fingerprint

    refresh(tmp_path, start="2025-07-01", end="2025-07-08", now=NOW, session=Session())
    pointer_path = tmp_path / "data/external/treasury/latest.json"
    pointer = json.loads(pointer_path.read_text())
    metadata_path = tmp_path / pointer["metadata_path"]
    metadata = json.loads(metadata_path.read_text())
    metadata[field] = value
    metadata_path.write_text(json.dumps(metadata))
    pointer["metadata_sha256"] = fingerprint(metadata_path)
    pointer_path.write_text(json.dumps(pointer))
    with pytest.raises(ValueError, match="summary differs"):
        load_snapshot(tmp_path)
