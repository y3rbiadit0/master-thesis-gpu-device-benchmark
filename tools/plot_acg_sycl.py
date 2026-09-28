# /// script
# requires-python = ">=3.10"
# dependencies = ["matplotlib==3.10.6"]
# ///
"""Render the SYCL/CUDA aCG comparison: uv run tools/plot_acg_sycl.py.

Reads the files written by tools/import_acg_sycl_evidence.py. Native and SYCL
series come from the same allocations; the main-campaign NCCL series is drawn
for reference only.
"""

import csv
import importlib.util
import statistics as stats
from collections import defaultdict
from pathlib import Path

spec = importlib.util.spec_from_file_location("plots", Path(__file__).parent / "plot_main_evidence.py")
plots = importlib.util.module_from_spec(spec)
spec.loader.exec_module(plots)
plt = plots.plt

MATRICES = ("Bump_2911", "Queen_4147")
# (backend, trials file, label, color, marker, line style)
SERIES = (
    ("acg-cg-mpi", "native", "MPI", "#2878b5", "o", "-"),
    ("acg-cg-nccl", "native", "NCCL", "#dc652c", "s", "-"),
    ("acg-sycl-mpi", "sycl", "SYCL MPI", "#8651a6", "v", "--"),
    ("acg-sycl-oneccl-nccl", "sycl", "SYCL oneCCL/NCCL", "#a04a76", "P", "--"),
)
SINGLE = {"native": "acg-cg-single", "sycl": "acg-sycl-single"}
UP, OUT = (1, 2, 4), (4, 8, 16, 32)


def valid_times(rows):
    times = defaultdict(list)
    for r in rows:
        if r["status"] == "valid":
            times[(r["matrix"], r["backend"], int(r["ranks"]))].append(float(r["solver_s"]))
    return times


def ticks(ax, values):
    ax.set_xscale("log", base=2)
    ax.set_yscale("log", base=2)
    ax.set_xticks(values, [str(v) for v in values])
    plots.frame(ax)


def scaling(times, archived):
    """Strong-scaling speedup over the native single-GPU median, split into
    scaling up (one node) and scaling out (full nodes), as in the aCG paper."""
    fig, axes = plt.subplots(2, 2, figsize=(9.5, 6.4), layout="constrained")
    for row, matrix in enumerate(MATRICES):
        reference = stats.median(times[(matrix, SINGLE["native"], 1)])
        for col, (gpus, title) in enumerate(((UP, "scaling up, one node"), (OUT, "scaling out, 4 GPUs per node"))):
            ax = axes[row, col]
            ax.plot(gpus, [g / gpus[0] * (1 if col == 0 else reference / stats.median(
                times[(matrix, "acg-cg-nccl", 4)])) for g in gpus], "k:", linewidth=0.9,
                label="Ideal")
            for backend, side, label, color, marker, style in SERIES:
                points = [g for g in gpus if (matrix, backend if g > 1 else SINGLE[side], g) in times]
                cells = [times[(matrix, backend if g > 1 else SINGLE[side], g)] for g in points]
                ax.plot(points, [reference / stats.median(c) for c in cells], color=color, marker=marker,
                        linestyle=style, label=label, markersize=4, linewidth=1.3)
                ax.fill_between(points, [reference / max(c) for c in cells], [reference / min(c) for c in cells],
                                color=color, alpha=0.12, linewidth=0)
            if col == 1:
                ref = [g for g in gpus if (matrix, "acg-cg-nccl", g) in archived]
                ax.plot(ref, [reference / stats.median(archived[(matrix, "acg-cg-nccl", g)]) for g in ref],
                        color="#7f7f7f", marker="s", markerfacecolor="white", linestyle=":", linewidth=1.0,
                        markersize=3.5, label="NCCL, main campaign")
            ax.set(title=f"{matrix}: {title}", xlabel="GPUs", ylabel="Speedup over native 1 GPU")
            ticks(ax, gpus)
    axes[0, 0].legend(fontsize=7)
    axes[0, 1].legend(fontsize=7)
    plots.save(fig, "acg-sycl-scaling.png")


def ratios(sycl_rows, native_rows):
    """SYCL / native per allocation (points) and median over allocations (line)."""
    fig, axes = plt.subplots(1, 2, figsize=(9.5, 3.8), layout="constrained")
    by_job = defaultdict(list)
    for r in sycl_rows + native_rows:
        if r["status"] == "valid":
            by_job[(r["matrix"], r["backend"], int(r["ranks"]), r["job"])].append(float(r["solver_s"]))
    for ax, matrix in zip(axes, MATRICES):
        ax.axhline(1, color="black", linewidth=0.8)
        ax.axvspan(4.6, 40, color="#000000", alpha=0.04, linewidth=0)
        for pair, sycl_label, native_label, label, color, marker, style in (
            ("single", "acg-sycl-single", "acg-cg-single", "Single GPU", "black", "*", "-"),
            ("mpi", "acg-sycl-mpi", "acg-cg-mpi", "SYCL MPI / MPI", "#8651a6", "v", "--"),
            ("nccl", "acg-sycl-oneccl-nccl", "acg-cg-nccl", "SYCL oneCCL/NCCL / NCCL", "#a04a76", "P", "-"),
        ):
            xs, medians = [], []
            for ranks in (1, 2, 4, 8, 16, 32):
                points = [stats.median(times) / stats.median(by_job[(matrix, native_label, ranks, job)])
                          for (m, b, p, job), times in sorted(by_job.items())
                          if (m, b, p) == (matrix, sycl_label, ranks) and (matrix, native_label, ranks, job) in by_job]
                if not points:
                    continue
                ax.scatter([ranks] * len(points), points, color=color, marker=marker, s=14, alpha=0.45,
                           linewidths=0)
                xs.append(ranks)
                medians.append(stats.median(points))
            if len(xs) > 1:
                ax.plot(xs, medians, color=color, marker=marker, linestyle=style, label=label, markersize=4,
                        linewidth=1.3)
            else:
                ax.scatter(xs, medians, color=color, marker=marker, s=40, label=label, zorder=3)
        ax.text(5.2, 3.2, "across nodes", fontsize=7, color="#555555")
        ax.set(title=matrix, xlabel="GPUs", ylabel="SYCL / native solver time")
        ticks(ax, (1, 2, 4, 8, 16, 32))
        ax.set_ylim(0.03, 4)
        ax.set_yticks([0.03125, 0.125, 0.5, 1, 2, 4], ["1/32", "1/8", "1/2", "1", "2", "4"])
    axes[0].legend(fontsize=7, loc="lower left")
    plots.save(fig, "acg-sycl-ratio.png")


def main():
    plt.rcParams.update({"font.size": 9, "axes.titlesize": 10, "legend.fontsize": 8})
    sycl = plots.read("acg-sycl-trials.csv")
    native = plots.read("acg-sycl-native-trials.csv")
    archived = valid_times(plots.read("acg-trials.csv"))
    scaling(valid_times(sycl + native), archived)
    ratios(sycl, native)


if __name__ == "__main__":
    main()
