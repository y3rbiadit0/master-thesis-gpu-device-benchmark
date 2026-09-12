# /// script
# requires-python = ">=3.10"
# dependencies = ["matplotlib==3.10.6"]
# ///
"""Render supplied NCCL summary medians; no inference from missing raw trials.

Run from any directory: uv run tools/plot_nccl_preliminary.py
Input provenance is documented in data/nccl-preliminary.md.
"""

import csv
from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt


ROOT = Path(__file__).resolve().parents[1]
RESULTS = ROOT / "data"
FIGURES = ROOT / "figures/results"
SERIES = (
    ("nccl_2_18_5_us", "2.18.5 / plain", "#105eba", "o"),
    ("nccl_2_31_2_plain_us", "2.31.2 / plain", "#6c747d", "s"),
    ("nccl_2_31_2_symmetric_us", "2.31.2 / symmetric", "#c41e2d", "^"),
)


def main():
    with (RESULTS / "nccl-preliminary.csv").open(newline="") as source:
        rows = list(csv.DictReader(source))
    for operation in ("allreduce", "alltoall"):
        selected = [row for row in rows if row["operation"] == operation]
        sizes = [int(row["size_bytes"]) for row in selected]
        fig, (latency, speedup) = plt.subplots(
            2, 1, figsize=(8, 5.6), sharex=True,
            gridspec_kw={"height_ratios": [2, 1]}, layout="constrained",
        )
        for column, label, color, marker in SERIES:
            values = [float(row[column]) for row in selected]
            latency.plot(sizes, values, label=label, color=color, marker=marker,
                         markersize=3, linewidth=1.3)
        for column, label, color, marker in SERIES[:2]:
            ratios = [float(row[column]) / float(row[SERIES[2][0]]) for row in selected]
            speedup.plot(sizes, ratios, label=f"{label} / symmetric",
                         color=color, marker=marker, markersize=3, linewidth=1.3)
        latency.set_yscale("log")
        latency.set_ylabel("Median latency (µs; lower is better)")
        latency.legend(loc="upper left", fontsize=9)
        latency.set_title(f"Preliminary NCCL {operation}: one node, four A100 GPUs")
        speedup.axhline(1, color="black", linewidth=0.8, linestyle="--")
        speedup.set_ylabel("Speedup\n(reference / symmetric)")
        speedup.set_xlabel("Reported size (bytes; original size convention retained)")
        for ax in (latency, speedup):
            ax.set_xscale("log", base=2)
            ax.grid(True, which="major", alpha=0.2)
        ticks = [4, 64, 1024, 16384, 262144, 4194304, 16777216]
        labels = ["4 B", "64 B", "1 KiB", "16 KiB", "256 KiB", "4 MiB", "16 MiB"]
        valid_ticks = [(x, label) for x, label in zip(ticks, labels) if x >= sizes[0]]
        speedup.set_xticks([x for x, _ in valid_ticks], [label for _, label in valid_ticks])
        if operation == "allreduce":
            latency.annotate("4 B plain-2.31.2 anomaly\n(retained from summary)",
                             xy=(4, 27.7), xytext=(128, 48), fontsize=8,
                             arrowprops={"arrowstyle": "->", "color": "#6c747d"})
        output = FIGURES / f"nccl-preliminary-{operation}.png"
        fig.savefig(output, dpi=220)
        plt.close(fig)
        print(output)


if __name__ == "__main__":
    main()
