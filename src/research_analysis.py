"""Export validated empirical tables and build reproducible research figures."""

from datetime import datetime, timezone
from decimal import Decimal
import json
from pathlib import Path
import shutil
import subprocess
from urllib.parse import urlparse

import pandas as pd

from .research_overview import ROOT, overview_payload
from .research_ledger import fingerprint, local_path, require
from .treasury import load_snapshot
from .treasury_crosscheck import load_crosscheck

REVIEWED_HOSTS = {
    "epuc.vermont.gov",
    "puc.vermont.gov",
    "fileservice.eea.comacloud.net",
    "www.dpuc.state.ct.us",
    "mpuc-cms.maine.gov",
    "www.puc.nh.gov",
    "www.mass.gov",
    "ripuc.ri.gov",
    "docs.cpuc.ca.gov",
    "researchonline.lse.ac.uk",
    "psc.ky.gov",
    "unitilcorp.gcs-web.com",
    "interchange.puc.texas.gov",
    "efis.psc.mo.gov",
    "pscdocs.utah.gov",
    "documents.dps.ny.gov",
    "fred.stlouisfed.org",
    "api.stlouisfed.org",
    "home.treasury.gov",
    "www.eei.org",
}


def dec(value):
    return None if value is None else float(Decimal(value))


def tables_from_payload(p):
    proposed = set(p["sample"]["proposed_ids"])
    outcomes = []
    for r in p["insights"]["outcomes"]:
        row = {
            k: r[k] for k in ("case_id", "utility", "state", "docket", "order_date", "award_kind")
        }
        row.update(
            proposed=int(r["case_id"] in proposed),
            final_sample=int(p["sample"]["status"] == "finalized" and r["case_id"] in proposed),
            gap_bp=dec(r["award_minus_request_bp"]),
        )
        for role in ("request", "award"):
            f = r[role]
            row.update(
                {
                    role + "_pct": dec(f["value"]) if f else None,
                    role + "_page": f["page"] if f else None,
                    role + "_field": f["field"] if f else "",
                    role + "_url": f["source_url"] if f else "",
                    role + "_sha256": f["pdf_sha256"] if f else "",
                }
            )
        row["pair_status"] = (
            "matched_original_values" if row["gap_bp"] is not None else "missing_request_or_award"
        )
        outcomes.append(row)
    coding = []
    for r in p["insights"]["coding_rows"]:
        for code, counts in r["codes"].items():
            n = r["commission_units"]
            stance = counts["stances"]
            coding.append(
                dict(
                    case_id=r["case_id"],
                    utility=r["utility"],
                    state=r["state"],
                    code=code,
                    denominator=n,
                    relied=stance["Relied on"],
                    considered=stance["Considered"],
                    rejected=stance["Rejected"],
                    absent=n - counts["present"],
                    relied_pct=100 * stance["Relied on"] / n,
                    considered_pct=100 * stance["Considered"] / n,
                    rejected_pct=100 * stance["Rejected"] / n,
                    absent_pct=100 * (n - counts["present"]) / n,
                )
            )
    coded_ids = {r["case_id"] for r in p["insights"]["coding_rows"]}
    source = {s["source_id"]: s for s in p["sources"]}
    units = []
    for u in p["passages"]:
        if u["case_id"] not in coded_ids or u["section"] != "Commission analysis":
            continue
        s = source[u["source_id"]]
        for code in ("MKT", "PEER", "OWN"):
            units.append(
                dict(
                    case_id=u["case_id"],
                    passage_id=u["passage_id"],
                    unit_type=u["unit_type"],
                    code=code,
                    present=u["codes"][code],
                    stance=u["stances"].get(code, ""),
                    pages=";".join(str(span["page"]) for span in u["spans"]),
                    source_url=s["source_url"],
                    pdf_sha256=s["pdf_sha256"],
                )
            )
    bench_sources = {s["source_id"]: s for s in p["benchmarks"]["sources"]}
    benchmarks = [
        dict(
            benchmark_id=r["benchmark_id"],
            service=r["service"],
            period_start=r["period_start"],
            period_end=r["period_end"],
            published_date=r["published_date"],
            mean_pct=dec(r.get("display_percent") or r["printed_percent"]),
            dataset_version=r["dataset_version"],
            estimation_method=r.get("estimation_method", "publisher_reported"),
            riders_excluded=int(r["riders_excluded"]),
            source_url=bench_sources[r["source_id"]]["source_url"],
            source_page=r["evidence"]["page"],
            pdf_sha256=bench_sources[r["source_id"]]["pdf_sha256"],
        )
        for r in p["benchmarks"]["records"]
    ]
    candidates = {c["candidate_id"]: c for c in p["sample"]["candidates"]}
    joins = [
        dict(
            case_id=j["candidate_id"],
            state=candidates[j["candidate_id"]]["state"],
            utility=candidates[j["candidate_id"]]["utility"],
            service=j["service"],
            order_date=j["order_date"],
            period_start=j["required_period_start"],
            period_end=j["required_period_end"],
            status=j["status"],
            benchmark_pct=dec(j.get("display_percent") or j["printed_percent"]),
            benchmark_id=j["benchmark_id"] or "",
            estimation_method=j.get("estimation_method") or "",
            available_at_order=int(j["available_at_written_date"])
            if j["available_at_written_date"] is not None
            else None,
        )
        for j in p["benchmarks"]["joins"]
    ]
    daily, matched = [], []
    if p["treasury"]:
        daily = [
            dict(
                observation_date=r["date"],
                yield_pct=dec(r["percent"]) if r["percent"] not in ("", ".", "NA") else None,
            )
            for r in p["treasury"]["series"]
        ]
        numeric = {r["case_id"]: r for r in outcomes}
        for j in p["treasury"]["joins"]:
            r = numeric.get(j["case_id"])
            if r is None:
                continue
            y = None if j["value_fraction"] is None else Decimal(j["value_fraction"]) * 100
            matched.append(
                dict(
                    case_id=j["case_id"],
                    utility=r["utility"],
                    state=r["state"],
                    order_date=r["order_date"],
                    observation_date=j.get("observation_date"),
                    status=j["status"],
                    gap_days=j.get("gap_days"),
                    yield_pct=float(y) if y is not None else None,
                    award_pct=r["award_pct"],
                    award_kind=r["award_kind"],
                    spread_bp=float((Decimal(str(r["award_pct"])) - y) * 100)
                    if y is not None and r["award_pct"] is not None
                    else None,
                )
            )
    gap_checks = [
        dict(
            omitted_case_id=r["omitted_case_id"],
            remaining_pairs=r["remaining_pairs"],
            median_bp=dec(r["median_bp"]),
        )
        for r in p["insights"]["sensitivity"]["request_gap"]["leave_one_out"]
    ]
    weighting = [
        dict(
            code=r["code"],
            orders=r["orders"],
            commission_units=r["commission_units"],
            reliance_units=r["reliance_units"],
            pooled_pct=dec(r["pooled_percent"]),
            equal_order_pct=dec(r["equal_order_percent"]),
        )
        for r in p["insights"]["sensitivity"]["reliance_weighting"]
    ]
    comparisons = [
        dict(
            case_id=r["case_id"],
            service=r["service"],
            award_pct=dec(r["award"]["value"]),
            award_kind=r["award_kind"],
            comparison_basis=r["comparison_basis"],
            timing_note=r["timing_note"],
            benchmark_id=r["benchmark"]["benchmark_id"],
            benchmark_pct=dec(
                r["benchmark"].get("display_percent") or r["benchmark"]["printed_percent"]
            ),
            published_at_decision=int(r["published_at_decision"]),
            award_minus_benchmark_bp=dec(r["award_minus_benchmark_bp"]),
        )
        for r in p["insights"]["benchmark_comparisons"]
    ]
    result = dict(
        outcomes=outcomes,
        coding=coding,
        commission_units=units,
        benchmarks=benchmarks,
        benchmark_joins=joins,
        treasury_daily=daily,
        treasury_orders=matched,
        request_gap_sensitivity=gap_checks,
        reliance_weighting=weighting,
        benchmark_comparisons=comparisons,
    )
    if p.get("cohort"):
        numeric = {r["case_id"]: r for r in outcomes}
        result["cohort_members"] = [
            dict(
                case_id=c["candidate_id"],
                state=c["state"],
                utility=c["utility"],
                docket=c["docket"],
                order_date=c["order_date"],
                stratum=c["stratum"],
                proceeding_group=c["proceeding_group"],
                services=";".join(c["services"]),
                eligibility=c["status"],
                award_pct=numeric.get(c["candidate_id"], {}).get("award_pct"),
                request_pct=numeric.get(c["candidate_id"], {}).get("request_pct"),
            )
            for c in p["cohort"]["members"]
        ]
        result["cohort_benchmark_joins"] = [
            dict(
                case_id=j["candidate_id"],
                service=j["service"],
                period_start=j["required_period_start"],
                period_end=j["required_period_end"],
                status=j["status"],
                benchmark_pct=dec(j.get("display_percent") or j.get("printed_percent")),
                benchmark_id=j.get("benchmark_id") or "",
                available_at_order=int(j["available_at_written_date"])
                if j["available_at_written_date"] is not None
                else None,
            )
            for j in p["cohort_benchmarks"]["joins"]
        ]
    if p.get("eei"):
        result["eei_benchmarks"] = [
            dict(
                benchmark_id=r["benchmark_id"],
                service=r["service"],
                period_start=r["period_start"],
                period_end=r["period_end"],
                source_vintage=r["source_vintage"],
                mean_pct=dec(r["display_percent"]),
                unrounded_pct=dec(r["unrounded_percent"]),
                n_observed=r["n_observed"],
                n_missing=r["n_missing"],
                sum_percent=dec(r["sum_percent"]),
                retrospective=1,
                source_sha256=p["eei"]["sources"][0]["sha256"],
            )
            for r in p["eei"]["records"]
            if r["scope"] == "base_rate_electric"
        ]
    return result


def source_inventory(root, p, crosscheck):
    rows = []
    for s in (
        p["sources"] + p["benchmarks"]["sources"] + p.get("audit", {}).get("context_sources", [])
    ):
        rows.append(
            dict(
                source_id=s["source_id"],
                kind=s.get("source_kind", "commission_filed_rra_report"),
                url=s["source_url"],
                local_path=s["pdf_path"],
                sha256=s["pdf_sha256"],
            )
        )
    if p.get("eei"):
        for s in p["eei"]["sources"]:
            rows.append(
                dict(
                    source_id=s["source_id"],
                    kind="public_industry_workbook",
                    url=s["url"],
                    local_path=s["path"],
                    sha256=s["sha256"],
                )
            )
    if p["treasury"]:
        meta, _ = load_snapshot(root)
        rows.append(
            dict(
                source_id="FRED-DGS10",
                kind="official_daily_series",
                url=meta["request_url"],
                local_path=meta["raw_path"],
                sha256=meta["raw_sha256"],
            )
        )
    if crosscheck:
        for s in crosscheck["sources"]:
            rows.append(
                dict(
                    source_id="TREASURY-XML-" + str(s["year"]),
                    kind="official_daily_series_crosscheck",
                    url=s["request_url"],
                    local_path=s["raw_path"],
                    sha256=s["raw_sha256"],
                )
            )
    require(len({r["source_id"] for r in rows}) == len(rows), "Analysis source IDs are duplicated")
    for r in rows:
        parsed = urlparse(r["url"])
        require(
            parsed.scheme == "https" and parsed.hostname in REVIEWED_HOSTS,
            "Analysis source endpoint is outside reviewed institutions: " + r["source_id"],
        )
        require(
            fingerprint(local_path(root, r["local_path"])) == r["sha256"],
            "Analysis source bytes differ",
        )
        r["host"] = parsed.hostname
        r["check"] = "reviewed_endpoint_and_saved_bytes"
    return rows


def reconstruction_rows(root, payload):
    """Export the full source table, including missing ROEs and excluded riders."""
    rows = []
    paths = sorted(
        {
            r["reconstruction"]["path"]
            for r in payload["benchmarks"]["records"]
            if r.get("estimation_method") == "case_level_reconstruction"
        }
    )
    for path in paths:
        raw = json.loads(local_path(root, path).read_text())
        for r in raw["rows"]:
            e = r["evidence"]
            rows.append(
                dict(
                    row_id=r["row_id"],
                    source_id=raw["source_id"],
                    service=r["service"],
                    decision_date=r["decision_date"],
                    company=r["company"],
                    state=r["state"],
                    roe_pct=dec(r["roe_percent"]),
                    limited_issue_rider=int(r["limited_issue_rider"]),
                    included_h2=int(
                        r["roe_percent"] is not None
                        and not r["limited_issue_rider"]
                        and "2019-07-01" <= r["decision_date"] <= "2019-12-31"
                    ),
                    source_page=e["page"],
                    start_char=e["start_char"],
                    end_char=e["end_char"],
                    pdf_sha256=raw["pdf_sha256"],
                )
            )
    return rows


def write_table(rows, path):
    df = pd.DataFrame(rows)
    require(not df.empty, "Analysis table is empty: " + path.stem)
    for col in df:
        if col.endswith("_date") or col in ("period_start", "period_end"):
            df[col] = pd.to_datetime(df[col]).dt.as_unit("ns")
        elif df[col].dtype == "object":
            df[col] = df[col].fillna("")
    df.to_csv(path.with_suffix(".csv"), index=False, date_format="%Y-%m-%d", float_format="%.12g")
    dates = {col: "td" for col in df if pd.api.types.is_datetime64_any_dtype(df[col])}
    df.to_stata(
        path.with_suffix(".dta"),
        write_index=False,
        version=118,
        convert_dates=dates,
        data_label="Anchored Returns: real candidate evidence; provisional sample",
        time_stamp=datetime(2000, 1, 1),
    )
    reread = pd.read_stata(
        path.with_suffix(".dta"), convert_categoricals=False, preserve_dtypes=False
    )
    for col in dates:
        reread[col] = reread[col].dt.as_unit("ns")
    pd.testing.assert_frame_equal(
        df, reread, check_dtype=False, check_exact=False, atol=1e-10, rtol=1e-10
    )
    return dict(
        rows=len(df),
        columns=list(df),
        csv_sha256=fingerprint(path.with_suffix(".csv")),
        dta_sha256=fingerprint(path.with_suffix(".dta")),
        stata_roundtrip="passed",
    )


def python_figures(tables, directory):
    import matplotlib

    matplotlib.use("Agg")
    import matplotlib.pyplot as plt
    import matplotlib.dates as mdates
    from matplotlib.colors import ListedColormap

    plt.rcParams.update(
        {
            "font.family": "DejaVu Sans",
            "font.size": 10,
            "axes.spines.top": False,
            "axes.spines.right": False,
            "axes.edgecolor": "#CBD2D3",
            "axes.labelcolor": "#263638",
            "text.color": "#263638",
            "xtick.color": "#526366",
            "ytick.color": "#526366",
            "savefig.facecolor": "white",
        }
    )
    directory.mkdir(exist_ok=True)
    files = []

    def save(fig, name):
        for ext in ("png", "pdf", "svg"):
            path = directory / (name + "." + ext)
            fig.savefig(path, dpi=200, bbox_inches="tight")
            files.append(str(path))
        plt.close(fig)

    rows = tables["benchmark_joins"]
    # One line per service. Joint orders retain distinct service matches.
    labels = [
        r["state"]
        + " "
        + r["case_id"].replace("CAND-" + r["state"] + "-", "")
        + " / "
        + r["service"]
        for r in rows
    ]
    periods = sorted({r["period_start"] for r in rows})
    grid = [[float("nan") for _ in periods] for _ in rows]
    for i, r in enumerate(rows):
        grid[i][periods.index(r["period_start"])] = int(r["status"] == "matched")
    fig, ax = plt.subplots(figsize=(11, 8.5))
    colors = ListedColormap(["#D5A875", "#207A77"])
    colors.set_bad("#F2F4F3")
    ax.imshow(grid, cmap=colors, vmin=0, vmax=1, aspect="auto")
    ax.set_yticks(range(len(labels)), labels, fontsize=8.5)
    ax.set_xticks(
        range(len(periods)),
        [s[:4] + (" H1" if s[5:7] == "01" else " H2") for s in periods],
        rotation=40,
        ha="right",
    )
    for i, r in enumerate(rows):
        x = periods.index(r["period_start"])
        ax.text(
            x,
            i,
            "Verified" if r["status"] == "matched" else "Missing",
            ha="center",
            va="center",
            fontsize=8,
            color="white" if r["status"] == "matched" else "#263638",
        )
    ax.set_title(
        "Original pilot: strict RRA benchmark coverage", loc="left", fontweight="bold", pad=20
    )
    ax.set_xlabel("Required previous half-year")
    fig.text(
        0.01,
        0.015,
        "Sources: original RRA tables filed with state commissions. Same service; general rate cases excluding riders.\n"
        "H2 2019 is reconstructed from the complete decision table. Gray cells are not required; the 15-order proposal remains provisional.",
        fontsize=9,
    )
    fig.subplots_adjust(left=0.31, bottom=0.17, top=0.91)
    save(fig, "benchmark_coverage")
    daily = pd.DataFrame(tables["treasury_daily"])
    orders = pd.DataFrame(tables["treasury_orders"])
    if not daily.empty and not orders.empty:
        fig, axes = plt.subplots(
            2, 1, figsize=(11, 7.4), gridspec_kw={"height_ratios": [1.4, 1]}, sharex=True
        )
        dates = pd.to_datetime(daily["observation_date"])
        # Missing dates break the line; no holiday value is manufactured.
        axes[0].plot(dates, daily["yield_pct"], color="#207A77", lw=1, label="FRED DGS10")
        for kind, marker, color, label in [
            ("commission_determined", "o", "#D09550", "Original commission award"),
            ("approved_settlement", "D", "#687D99", "Approved settlement"),
        ]:
            sub = orders[(orders["award_kind"] == kind) & (orders["status"] == "matched")]
            axes[0].scatter(
                pd.to_datetime(sub["order_date"]),
                sub["award_pct"],
                marker=marker,
                color=color,
                s=44,
                edgecolors="white",
                zorder=3,
                label=label,
            )
            axes[1].scatter(
                pd.to_datetime(sub["order_date"]),
                sub["spread_bp"],
                marker=marker,
                color=color,
                s=44,
            )
        axes[0].set_ylabel("Annual rate (%)")
        axes[0].set_ylim(bottom=0)
        axes[0].set_title(
            "Entered awards and the interest-rate environment",
            loc="left",
            fontweight="bold",
            pad=20,
        )
        axes[0].legend(
            loc="center left", bbox_to_anchor=(0, 1.06), ncol=3, frameon=False, fontsize=9
        )
        axes[1].set_ylabel("Award less DGS10 (bp)")
        axes[1].set_ylim(bottom=0)
        for ax in axes:
            ax.grid(axis="y", color="#E9EEED")
            ax.set_axisbelow(True)
        axes[1].xaxis.set_major_locator(mdates.YearLocator())
        axes[1].xaxis.set_major_formatter(mdates.DateFormatter("%Y"))
        fig.text(
            0.02,
            0.02,
            "Sources: original orders and FRED DGS10, pinned retrieval vintage. Order dates use on-or-before matches.\n"
            "These spreads are descriptive rate differences, not estimated equity risk premiums or evidence of causal pass-through.",
            fontsize=9,
        )
        fig.subplots_adjust(left=0.10, right=0.98, bottom=0.16, top=0.88, hspace=0.22)
        save(fig, "treasury_context")
    return files


def analyze(root=ROOT, *, output=None, rscript=None, run_r=True):
    root = Path(root).resolve()
    p = overview_payload(root)
    crosscheck = load_crosscheck(root)
    tables = tables_from_payload(p)
    if p.get("eei"):
        from .eei_benchmarks import eei_report

        tables["eei_observations"] = [
            dict(
                source_row=r["source_row"],
                state=r["state"],
                utility=r["utility"],
                docket=r["docket"],
                completion_status=r["completion_status"],
                case_type=r["case_type"],
                requested_date=r["requested_date"],
                requested_roe_pct=dec(r["requested_roe_percent"]),
                authorized_date=r["authorized_date"],
                authorized_roe_pct=dec(r["authorized_roe_percent"]),
            )
            for r in eei_report(root)["rows"]
        ]
    reconstructed = reconstruction_rows(root, p)
    if reconstructed:
        tables["benchmark_decisions"] = reconstructed
    tables["sources"] = source_inventory(root, p, crosscheck)
    target = (
        Path(output).resolve()
        if output
        else root / "reports/analysis" / datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%S%fZ")
    )
    require(
        not target.exists(),
        "Use a new analysis directory; existing research releases are preserved",
    )
    target.mkdir(parents=True)
    data = target / "data"
    data.mkdir()
    manifests = {name: write_table(rows, data / name) for name, rows in tables.items()}
    python_files = python_figures(tables, target / "python")
    executable = rscript or shutil.which("Rscript")
    r_status = dict(
        status="not_run", reason="Rscript unavailable" if run_r else "Execution explicitly skipped"
    )
    if run_r and executable:
        rdir = target / "r"
        rdir.mkdir()
        result = subprocess.run(
            [executable, "--vanilla", str(root / "analysis/figures.R"), str(data), str(rdir)],
            capture_output=True,
            text=True,
            timeout=120,
        )
        (target / "r_run.log").write_text(result.stdout + result.stderr)
        require(
            result.returncode == 0,
            "R figure generation failed; inspect " + str(target / "r_run.log"),
        )
        checks = pd.read_csv(rdir / "checks.csv")
        expected = pd.DataFrame(
            [
                dict(case_id=r["case_id"], gap_bp=r["gap_bp"])
                for r in tables["outcomes"]
                if r["gap_bp"] is not None
            ]
        )
        pd.testing.assert_frame_equal(
            checks.sort_values("case_id").reset_index(drop=True),
            expected.sort_values("case_id").reset_index(drop=True),
            check_dtype=False,
            check_exact=False,
            atol=1e-8,
            rtol=1e-8,
        )
        r_status = dict(
            status="executed_and_numeric_crosscheck_passed",
            executable=executable,
            version=result.stdout.strip(),
            pairs_checked=len(checks),
        )
    scripts = {name: fingerprint(root / "analysis" / name) for name in ("figures.R", "figures.do")}
    code = {
        name: fingerprint(root / name)
        for name in (
            "src/research_analysis.py",
            "src/research_insights.py",
            "src/research_overview.py",
            "src/research_audit.py",
            "src/treasury_crosscheck.py",
            "src/research_benchmarks.py",
            "src/rra_reconstruction.py",
            "src/research_cohort.py",
            "src/cohort_facts.py",
            "src/eei_benchmarks.py",
        )
    }
    extra_inputs = dict(p["inputs"])
    if crosscheck:
        extra_inputs["data/external/treasury_official/latest.json"] = fingerprint(
            root / "data/external/treasury_official/latest.json"
        )
    report = dict(
        schema_version="1.0",
        data_kind="real_source_records",
        created_at_utc=datetime.now(timezone.utc).isoformat(),
        sample_status=p["sample"]["status"],
        final_sample_orders=p["stats"]["selected_orders"],
        entered_orders=len(tables["outcomes"]),
        request_award_pairs=p["insights"]["request_award_pairs"],
        document_cohort=p.get("cohort")
        and {
            k: p["cohort"][k]
            for k in ("version", "total", "primary", "supplemental", "census_complete")
        },
        coded_orders=p["insights"]["coded_orders"],
        commission_units=p["insights"]["commission_units"],
        source_records=len(tables["sources"]),
        source_audit="reviewed_endpoints_saved_bytes_and_upstream_evidence_checks_passed",
        input_sha256=extra_inputs,
        script_sha256=scripts,
        code_sha256=code,
        tables=manifests,
        r=r_status,
        stata=dict(
            status="prepared_not_executed",
            reason="No licensed Stata runtime was located.",
            version="Stata 14.2 or later; Unicode DTA format 118",
            datasets="All .dta files round-tripped through pandas; native Stata execution is pending.",
        ),
        treasury_crosscheck=None
        if not crosscheck
        else {
            k: crosscheck[k]
            for k in (
                "retrieved_at_utc",
                "overlapping_dates",
                "equal",
                "missing_value_dates",
                "disagreements",
                "order_checks",
                "latest_nonmissing",
            )
        },
        limits=p["insights"]["limits"],
        output_path=str(target),
    )
    report["file_sha256"] = {
        str(path.relative_to(target)): fingerprint(path)
        for path in target.rglob("*")
        if path.is_file()
    }
    (target / "manifest.json").write_text(json.dumps(report, indent=2) + "\n")
    if output is None:
        pointer = root / "reports/analysis/latest.json"
        pointer.write_text(
            json.dumps(
                dict(
                    manifest_path=str((target / "manifest.json").relative_to(root)),
                    manifest_sha256=fingerprint(target / "manifest.json"),
                ),
                indent=2,
            )
            + "\n"
        )
    return report
