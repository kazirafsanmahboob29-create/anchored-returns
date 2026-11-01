"""Draw the paper's figures from the reproduced panel and saved estimates."""

import json
from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parents[1]


def prior_awards():
    source = ROOT / "reports/filing-study/panel.csv"
    if not source.exists():
        raise SystemExit("Reproduce the filing study before rebuilding this figure.")
    frame = pd.read_csv(source)
    frame = frame[frame.prior_eligible]
    if len(frame) != 1135:
        raise ValueError("The figure sample differs from the paper's recorded input vintage")
    plt.rcParams.update({"font.family": "DejaVu Serif", "font.size": 10})
    fig, ax = plt.subplots(figsize=(7, 3.3))
    for label, part, color, marker in (
        ("1985-2004", frame[frame.year <= 2004], "#8b8b8b", "o"),
        ("2005-2024", frame[frame.year > 2004], "#202020", "^"),
    ):
        ax.scatter(
            part.known_prior,
            part.award,
            s=15,
            color=color,
            marker=marker,
            alpha=0.45,
            linewidths=0,
            label=f"{label} ({len(part)} records)",
        )
    ax.plot([7, 18.5], [7, 18.5], "--", color="#666666", lw=1, zorder=0)
    ax.set(
        xlabel="Award known before filing (%)",
        ylabel="Current authorized award (%)",
        xlim=(7, 18.5),
        ylim=(7, 18.5),
        xticks=[8, 10, 12, 14, 16, 18],
        yticks=[8, 10, 12, 14, 16, 18],
    )
    ax.spines[["top", "right"]].set_visible(False)
    ax.legend(frameon=False, loc="upper left", fontsize=9)
    ax.grid(color="#e6e6e6", linewidth=0.5)
    ax.set_axisbelow(True)
    fig.tight_layout()
    output = ROOT / "paper/figures/current-and-prior.png"
    output.parent.mkdir(exist_ok=True)
    fig.savefig(output, dpi=240, facecolor="white")
    plt.close(fig)
    print(output)


def prediction_errors():
    summary = json.loads((ROOT / "reports/filing-study/study.json").read_text())
    blocks = [b for b in summary["prediction_blocks"] if b["status"] == "available"]
    fig, ax = plt.subplots(figsize=(7, 3.2))
    positions = np.arange(len(blocks))
    styles = (
        ("prior", "Previous award", "#b5b5b5"),
        ("market_prior", "Financial model", "#777777"),
        ("with_request", "Add the request", "#222222"),
    )
    for j, (key, label, color) in enumerate(styles):
        values = [next(m["mae_bp"] for m in b["metrics"] if m["rule"] == key) for b in blocks]
        bars = ax.bar(positions + (j - 1) * 0.24, values, 0.24, label=label, color=color)
        ax.bar_label(bars, fmt="%.1f", fontsize=8, padding=3)
    ax.set(
        xticks=positions,
        xticklabels=[b["block"] for b in blocks],
        ylabel="Mean absolute error (basis points)",
        xlabel="Filing period",
        ylim=(0, 52),
    )
    ax.spines[["top", "right"]].set_visible(False)
    ax.legend(frameon=False, fontsize=8, loc="upper right")
    fig.tight_layout()
    output = ROOT / "paper/figures/prediction-errors.png"
    fig.savefig(output, dpi=240, facecolor="white")
    plt.close(fig)
    print(output)


def main():
    prior_awards()
    prediction_errors()


if __name__ == "__main__":
    main()
