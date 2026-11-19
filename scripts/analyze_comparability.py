"""Rebuild the original-order pilot tables and figures, without the EEI workbook."""

import csv
import json
from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np

from src.rate_case_comparisons import load_schedules, roe_sensitivity

ROOT = Path(__file__).resolve().parents[1]
DATA = ROOT / "data/research/comparability-v1/phase2"
OUT = ROOT / "reports/comparability"


def write_csv(path, rows, fields):
    with path.open("w", newline="") as stream:
        writer = csv.DictWriter(stream, fieldnames=fields, extrasaction="ignore")
        writer.writeheader()
        writer.writerows(rows)


def main():
    OUT.mkdir(parents=True, exist_ok=True)
    rows = load_schedules(DATA)
    facts = json.loads((DATA / "facts.json").read_text())["facts"]
    requests = json.loads((DATA / "requests.json").read_text())["requests"]
    fact_map = {f["fact_id"]: f for f in facts}
    request_map = {
        r["proceeding_id"]: fact_map[r["requested_roe_fact"]]["value"]
        for r in requests
        if r["plan_basis"] != "multi_year_alternative"
    }
    for row in rows:
        row["order_reported_request"] = request_map[row["proceeding_id"]]
    fields = [
        "schedule_id",
        "proceeding_id",
        "label",
        "state",
        "decision_date",
        "rate_year",
        "order_reported_request",
        "base_roe",
        "adjustment_roe",
        "applied_roe",
        "approved_equity_share",
        "approved_rate_base_usd",
        "equity_allowance_per_100",
        "annual_equity_allowance_usd",
    ]
    write_csv(OUT / "pilot_financials.csv", rows, fields)
    sensitivities = []
    for row in rows:
        if row["annual_equity_allowance_usd"] is None:
            continue
        for bp in (10, 25, 50):
            sensitivities.append(
                {
                    "schedule_id": row["schedule_id"],
                    "label": row["label"],
                    "change_bp": bp,
                    "rate_base_usd": row["approved_rate_base_usd"],
                    "equity_share": row["approved_equity_share"],
                    "annual_equity_component_change_usd": roe_sensitivity(
                        row["approved_rate_base_usd"], row["approved_equity_share"], bp
                    ),
                }
            )
    write_csv(OUT / "financial_sensitivity.csv", sensitivities, list(sensitivities[0]))
    numeric = [r for r in rows if r["applied_roe"] is not None]
    bridges = []
    for row in rows:
        if row["base_roe"] is None or row["adjustment_roe"] is None:
            continue
        request = row["order_reported_request"]
        gap = (request - row["applied_roe"]) * 10000
        adjustment_bp = row["adjustment_roe"] * 10000
        bridges.append(
            {
                "proceeding_id": row["proceeding_id"],
                "label": row["label"],
                "requested_roe": request,
                "base_roe": row["base_roe"],
                "adjustment_bp": adjustment_bp,
                "applied_roe": row["applied_roe"],
                "request_to_applied_gap_bp": gap,
                "adjustment_share_of_gap": -adjustment_bp / gap,
            }
        )
    result = {
        "date": "2026-10-31",
        "source_basis": "original_orders_only_no_EEI_rows",
        "proceedings": len({r["proceeding_id"] for r in rows}),
        "financial_schedules": len(rows),
        "proceedings_with_roe_and_equity": len({r["proceeding_id"] for r in numeric}),
        "schedules_with_roe_and_equity": len(numeric),
        "schedules_with_rate_base": len(sensitivities) // 3,
        "performance_bridges": bridges,
        "schedules": rows,
    }
    (OUT / "pilot_results.json").write_text(json.dumps(result, indent=2) + "\n")
    plt.rcParams.update(
        {
            "font.family": "DejaVu Sans",
            "font.size": 10,
            "axes.spines.top": False,
            "axes.spines.right": False,
            "axes.titleweight": "bold",
            "figure.dpi": 170,
        }
    )
    fig, ax = plt.subplots(figsize=(9, 3.7))
    labels = [r["label"] for r in bridges]
    y = np.arange(len(bridges))
    for i, row in enumerate(bridges):
        points = np.array([row["requested_roe"], row["base_roe"], row["applied_roe"]]) * 100
        ax.plot(points, [i] * 3, color="#aaaaaa", linewidth=2, zorder=1)
        for value, marker, color, name in zip(
            points,
            ["o", "s", "D"],
            ["#999999", "#326677", "#111111"],
            ["Order-reported request", "Selected base ROE", "Applied ROE"],
        ):
            ax.scatter(value, i, marker=marker, color=color, s=60, label=name if i == 0 else None)
            ax.annotate(
                f"{value:.2f}%",
                (value, i),
                xytext=(0, 12),
                textcoords="offset points",
                ha="center",
                fontsize=9,
            )
    ax.set_yticks(y, labels)
    ax.set_ylim(-0.55, len(bridges) - 0.4)
    ax.set_xlim(8, 10.6)
    ax.set_xlabel("Return on equity (%)")
    ax.set_title("Performance adjustments change the comparison", loc="left", pad=30)
    ax.legend(loc="lower right", frameon=False, fontsize=8)
    ax.grid(axis="x", alpha=0.15)
    fig.tight_layout()
    fig.savefig(OUT / "performance-adjustments.png")
    plt.close(fig)
    ordered = sorted(numeric, key=lambda r: r["equity_allowance_per_100"])
    fig, ax = plt.subplots(figsize=(9, 6.2))
    y = np.arange(len(ordered))
    ax.barh(y, [r["equity_allowance_per_100"] for r in ordered], color="#326677", height=0.65)
    ax.set_yticks(y, ["WMECo 2017" if r["label"] == "WMECo" else r["label"] for r in ordered])
    for i, row in enumerate(ordered):
        ax.text(
            row["equity_allowance_per_100"] + 0.04,
            i,
            f"${row['equity_allowance_per_100']:.3f}",
            va="center",
            fontsize=9,
        )
    ax.set_xlim(0, 6.2)
    ax.set_xlabel("Annual equity-return component per $100 of approved rate base")
    ax.set_title("The equity share changes the dollar allowance", loc="left", pad=15)
    ax.grid(axis="x", alpha=0.15)
    ax.set_axisbelow(True)
    fig.tight_layout()
    fig.savefig(OUT / "equity-component.png")
    plt.close(fig)
    print({k: v for k, v in result.items() if k not in {"schedules", "performance_bridges"}})


if __name__ == "__main__":
    main()
