# /// script
# requires-python = ">=3.10"
# dependencies = ["matplotlib==3.10.6"]
# ///
"""Render the reconciled CSV archive: uv run tools/plot_main_evidence.py."""

import csv
import statistics as stats
from collections import defaultdict
from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt

ROOT = Path(__file__).resolve().parents[1]
DATA = ROOT / "data/main-campaign"
OUT = ROOT / "figures/results"
SERIES = {"cuda_mpi": ("MPI", "#2878b5", "o"), "cuda_nccl": ("NCCL", "#dc652c", "s"),
          "cuda_nvshmem": ("NVSHMEM", "#159870", "^"), "oshmpi": ("OSHMPI", "#b48a00", "D"),
          "sycl_mpi": ("SYCL MPI", "#8651a6", "v"), "sycl_oneccl": ("oneCCL/NCCL", "#a04a76", "P"),
          "sycl_oneccl_oshmpi": ("oneCCL/OSHMPI", "#65727d", "X")}
NEIGHBOR_BACKENDS = ("cuda_mpi", "cuda_nccl", "cuda_nvshmem", "oshmpi", "sycl_mpi", "sycl_oneccl")
COLLECTIVE_BACKENDS = tuple(SERIES)


def read(name):
    with (DATA / name).open(newline="") as stream:
        return list(csv.DictReader(stream))


def save(fig, name):
    fig.savefig(OUT / name, dpi=220)
    plt.close(fig)
    print(OUT / name)


def frame(ax):
    ax.grid(True, alpha=0.2)
    ax.set_axisbelow(True)


def curves(ax, rows, xkey, backends=NEIGHBOR_BACKENDS, denominator=None, xdivisor=1):
    for backend in backends:
        label, color, marker = SERIES[backend]
        points = sorted((r for r in rows if r["backend"] == backend), key=lambda r: float(r[xkey]))
        if not points:
            continue
        xs = [float(r[xkey]) / xdivisor for r in points]
        divisor = [denominator[x] if denominator else 1 for x in xs]
        ys = [float(r["median_us"]) / d for r, d in zip(points, divisor)]
        ax.plot(xs, ys, label=label, color=color, marker=marker, markersize=3, linewidth=1.3)
        ax.fill_between(xs, [float(r["job_min_us"]) / d for r, d in zip(points, divisor)],
                        [float(r["job_max_us"]) / d for r, d in zip(points, divisor)], color=color, alpha=0.1)
    ax.set_xscale("log", base=2)
    ax.set_yscale("log", base=2 if denominator else 10)
    frame(ax)


def main():
    plt.rcParams.update({"font.size": 9, "axes.titlesize": 10, "legend.fontsize": 8})
    bench = read("benchmark-summary.csv")
    fig, axes = plt.subplots(1, 2, figsize=(9, 3.6), layout="constrained")
    for ax, topology in zip(axes, ("1n2g", "2n1g")):
        curves(ax, [r for r in bench if r["benchmark"] == "pingpong" and r["topology"] == topology], "bytes")
        ax.set(title=topology, xlabel="Directional payload (bytes)", ylabel="Half round-trip latency (µs)")
        ax.set_xticks([4, 1024, 262144, 16777216], ["4 B", "1 KiB", "256 KiB", "16 MiB"])
    axes[0].legend()
    save(fig, "pingpong-regimes.png")

    fig, axes = plt.subplots(2, 2, figsize=(9, 6), layout="constrained")
    for row, case in enumerate(("isolated", "steady")):
        for col, topology in enumerate(("1n4g", "8n4g")):
            ax = axes[row, col]
            curves(ax, [r for r in bench if (r["benchmark"], r["topology"], r["case"])
                        == ("halo_1d", topology, case)], "bytes")
            ax.set(title=f"{topology}: {case}", xlabel="Aggregate halo payload (bytes)", ylabel="Latency per exchange (µs)")
            ax.set_xticks([16, 1024, 65536, 16777216], ["16 B", "1 KiB", "64 KiB", "16 MiB"])
    axes[0, 0].legend()
    save(fig, "halo-regimes.png")

    for case in ("isolated", "steady"):
        fig, axes = plt.subplots(2, 3, figsize=(10.5, 6.3), layout="constrained")
        for ax, topology in zip(axes.flat, ("1n2g", "1n4g", "2n1g", "2n4g", "4n4g", "8n4g")):
            curves(ax, [r for r in bench if (r["benchmark"], r["topology"], r["case"])
                        == ("halo_1d", topology, case)], "bytes")
            ax.set(title=topology, xlabel="Aggregate payload (bytes)", ylabel="Latency/exchange (µs)")
        axes[0, 0].legend(fontsize=7)
        save(fig, f"halo-{case}-all-topologies.png")

    fig, axes = plt.subplots(1, 3, figsize=(10.5, 3.5), layout="constrained")
    for ax, topology in zip(axes, ("1n4g", "2n4g", "8n4g")):
        curves(ax, [r for r in bench if r["benchmark"] == "allreduce" and r["topology"] == topology],
               "bytes", COLLECTIVE_BACKENDS)
        ax.set(title=topology, xlabel="Input payload (bytes)", ylabel="Complete allreduce latency (µs)")
        ax.set_xticks([4, 4096, 65536, 16777216], ["4 B", "4 KiB", "64 KiB", "16 MiB"])
    axes[0].legend(fontsize=7)
    save(fig, "allreduce-backends.png")

    fig, axes = plt.subplots(2, 4, figsize=(12, 6.2), layout="constrained")
    for ax, topology in zip(axes.flat, ("1n1g", "1n2g", "1n4g", "2n1g", "2n4g", "4n4g", "8n4g")):
        curves(ax, [r for r in bench if r["benchmark"] == "allreduce" and r["topology"] == topology],
               "bytes", COLLECTIVE_BACKENDS)
        ax.set(title=topology, xlabel="Input bytes", ylabel="Latency (µs)")
    axes.flat[-1].set_visible(False)
    axes[0, 0].legend(fontsize=6)
    save(fig, "allreduce-all-topologies.png")

    fig, axes = plt.subplots(1, 3, figsize=(10.5, 3.5), layout="constrained")
    for ax, topology in zip(axes, ("1n4g", "2n4g", "8n4g")):
        nodes, gpus = (int(value) for value in topology.replace("g", "").split("n"))
        ranks = nodes * gpus
        curves(ax, [r for r in bench if r["benchmark"] == "alltoall" and r["topology"] == topology],
               "bytes", COLLECTIVE_BACKENDS, xdivisor=ranks)
        ax.set(title=topology, xlabel="Payload per peer (bytes)", ylabel="Complete all-to-all latency (µs)")
        ax.set_xticks([4, 512, 8192, 262144], ["4 B", "512 B", "8 KiB", "256 KiB"])
    axes[0].legend(fontsize=7)
    save(fig, "alltoall-backends.png")

    fig, axes = plt.subplots(2, 4, figsize=(12, 6.2), layout="constrained")
    for ax, topology in zip(axes.flat, ("1n1g", "1n2g", "1n4g", "2n1g", "2n4g", "4n4g", "8n4g")):
        nodes, gpus = (int(value) for value in topology.replace("g", "").split("n"))
        curves(ax, [r for r in bench if r["benchmark"] == "alltoall" and r["topology"] == topology],
               "bytes", COLLECTIVE_BACKENDS, xdivisor=nodes * gpus)
        ax.set(title=topology, xlabel="Bytes per peer", ylabel="Latency (µs)")
    axes.flat[-1].set_visible(False)
    axes[0, 0].legend(fontsize=6)
    save(fig, "alltoall-all-topologies.png")

    # Backend comparisons of cg_step use multi-rank topologies only: at 1n1g no
    # inter-rank communication happens, so a ratio between stacks there
    # measures local execution, which the single-GPU controls report instead.
    fig, axes = plt.subplots(2, 2, figsize=(9, 5.8), layout="constrained")
    for ax, topology in zip(axes.flat, ("1n2g", "1n4g", "2n4g", "8n4g")):
        selected = [r for r in bench if r["benchmark"] == "cg_step" and r["topology"] == topology]
        reference = {float(r["n"]): float(r["median_us"]) for r in selected if r["backend"] == "cuda_mpi"}
        curves(ax, selected, "n", tuple(SERIES), reference)
        ax.axhline(1, color="black", linestyle="--", linewidth=0.8)
        ax.set(title=topology, xlabel="Global grid side", ylabel="Step time / CUDA MPI")
        ax.set_xticks([512, 1024, 2048, 4096, 8192], ["512", "1024", "2048", "4096", "8192"])
    axes[0, 0].legend(ncol=2)
    save(fig, "cg-step-relative.png")

    fig, axes = plt.subplots(2, 3, figsize=(10.5, 6.2), layout="constrained")
    for ax, topology in zip(axes.flat, ("1n2g", "1n4g", "2n1g", "2n4g", "4n4g", "8n4g")):
        selected = [r for r in bench if r["benchmark"] == "cg_step" and r["topology"] == topology]
        reference = {float(r["n"]): float(r["median_us"]) for r in selected if r["backend"] == "cuda_mpi"}
        curves(ax, selected, "n", NEIGHBOR_BACKENDS, reference)
        ax.axhline(1, color="black", linestyle="--", linewidth=0.8)
        ax.set(title=topology, xlabel="Global grid side", ylabel="Time / CUDA MPI")
    axes[0, 0].legend(fontsize=6, ncol=2)
    save(fig, "cg-step-all-topologies.png")

    moe = read("moe-summary.csv")
    moe_topologies = ("1n1g", "1n2g", "1n4g", "2n1g", "2n4g", "4n4g", "8n4g")
    for name, routings, size in (("moe-routing-scaling.png", ("uniform", "locality80", "hotspot80"), (10.5, 3.6)),):
        fig, axes = plt.subplots(1, len(routings), figsize=size, layout="constrained")
        for ax, routing in zip(axes, routings):
            positions = {topology: index for index, topology in enumerate(moe_topologies)}
            for backend in NEIGHBOR_BACKENDS:
                label, color, marker = SERIES[backend]
                rows = [r for r in moe if (r["routing"], r["backend"]) == (routing, backend)]
                rows.sort(key=lambda r: positions[r["topology"]])
                xs = [positions[r["topology"]] for r in rows]
                ax.plot(xs, [float(r["median_us"]) for r in rows], label=label, color=color,
                        marker=marker, markersize=3.5, linewidth=1.3)
                ax.fill_between(xs, [float(r["job_min_us"]) for r in rows],
                                [float(r["job_max_us"]) for r in rows], color=color, alpha=0.1)
            # Everything left of the line stays on NVLink; everything right crosses InfiniBand.
            ax.axvline(positions["1n4g"] + 0.5, color="black", linestyle=":", linewidth=0.9)
            ax.set_yscale("log", base=10)
            ax.set_xticks(range(len(moe_topologies)), moe_topologies, rotation=45)
            ax.set(title=routing, xlabel="Placement (single node | multi-node)",
                   ylabel="Dispatch + combine latency (µs)")
            frame(ax)
        axes[0].legend(fontsize=7)
        save(fig, name)

    fig, ax = plt.subplots(figsize=(6.2, 3.6), layout="constrained")
    width, routings = 0.26, ("uniform", "locality80", "hotspot80")
    for offset, routing in zip((-width, 0.0, width), routings):
        rows = {r["backend"]: r for r in moe if (r["routing"], r["topology"]) == (routing, "8n4g")}
        heights = [float(rows[backend]["median_us"]) / float(rows["cuda_mpi"]["median_us"])
                   for backend in NEIGHBOR_BACKENDS]
        ax.bar([index + offset for index in range(len(NEIGHBOR_BACKENDS))], heights, width,
               label=routing, edgecolor="black", linewidth=0.4)
    ax.axhline(1, color="black", linestyle="--", linewidth=0.8)
    ax.set_xticks(range(len(NEIGHBOR_BACKENDS)), [SERIES[b][0] for b in NEIGHBOR_BACKENDS], rotation=30, ha="right")
    ax.set(ylabel="Latency / CUDA MPI at 8n4g", xlabel="")
    ax.legend(fontsize=8)
    frame(ax)
    save(fig, "moe-routing-sensitivity.png")

    predictions = read("reduction-predictions.csv")
    fig, axes = plt.subplots(1, 2, figsize=(9, 3.7), layout="constrained")
    for ax, matrix in zip(axes, ("Bump_2911", "Queen_4147")):
        ax.plot([10, 55], [10, 55], "k--", linewidth=0.8, label="Exact agreement")
        for backend in ("cuda_mpi", "cuda_nccl"):
            label, color, marker = SERIES[backend]
            rows = [r for r in predictions if r["matrix"] == matrix and r["backend"] == backend]
            ax.scatter([float(r["predicted_us"]) for r in rows], [float(r["observed_us"]) for r in rows],
                       color=color, marker=marker, label=label)
            for r in rows:
                ax.annotate(r["ranks"], (float(r["predicted_us"]), float(r["observed_us"])),
                            xytext=(3, 4), textcoords="offset points", fontsize=7)
        ax.set(title=matrix, xlabel="CG-step estimate (µs per reduction)", ylabel="aCG observed interval (µs)")
        frame(ax)
    axes[0].legend()
    save(fig, "acg-reduction-prediction.png")

    summaries, trials = read("acg-summary.csv"), read("acg-trials.csv")
    fig, axes = plt.subplots(1, 2, figsize=(9.5, 3.8), layout="constrained")
    solver_series = (
        ("acg-cg-mpi", "MPI", "#2878b5", "o", "-"),
        ("acg-cg-nccl", "NCCL", "#dc652c", "s", "-"),
        ("acg-cg-nvshmem", "NVSHMEM (host)", "#159870", "^", "-"),
        ("acg-cg-oshmpi", "OSHMPI halo / MPI sum", "#b48a00", "D", "-"),
        ("acg-device-nvshmem", "NVSHMEM (device)", "#a04a76", "P", "--"),
    )
    for ax, matrix in zip(axes, ("Bump_2911", "Queen_4147")):
        single = next(r for r in summaries if r["matrix"] == matrix and r["backend"] == "acg-cg-single")
        ax.scatter([1], [float(single["median_solver_s"])], color="black", marker="*", label="Single GPU")
        for backend, label, color, marker, style in solver_series:
            rows = sorted((r for r in summaries if r["matrix"] == matrix and r["backend"] == backend),
                          key=lambda r: int(r["ranks"]))
            ax.plot([int(r["ranks"]) for r in rows], [float(r["median_solver_s"]) for r in rows],
                    color=color, marker=marker, linestyle=style, label=label, markersize=4)
        ax.set(title=matrix, xlabel="GPUs", ylabel="Median completed-trial solver time (s)")
        ax.set_xscale("log", base=2)
        ax.set_yscale("log", base=10)
        ax.set_xticks([1, 2, 4, 8, 16, 32], ["1", "2", "4", "8", "16", "32"])
        frame(ax)
    axes[0].legend(fontsize=7)
    save(fig, "acg-backend-median.png")

    fig, axes = plt.subplots(2, 2, figsize=(9.5, 6), layout="constrained")
    for i, matrix in enumerate(("Bump_2911", "Queen_4147")):
        left, right = axes[i]
        baseline = next(float(r["gflops_per_gpu"]) for r in summaries
                        if r["matrix"] == matrix and r["backend"] == "acg-cg-single")
        left.plot([1, 32], [1, 32], "k:", label="Ideal")
        for backend, label, color, marker, style in (
            ("acg-cg-nccl", "NCCL", "#dc652c", "s", "-"),
            ("acg-cg-nvshmem", "NVSHMEM (host)", "#159870", "^", "-"),
            ("acg-cg-oshmpi", "OSHMPI halo / MPI sum", "#b48a00", "D", "-"),
            ("acg-device-nvshmem", "NVSHMEM (device)", "#a04a76", "o", "--"),
        ):
            rows = sorted((r for r in summaries if r["matrix"] == matrix and r["backend"] == backend), key=lambda r: int(r["ranks"]))
            left.plot([1] + [int(r["ranks"]) for r in rows],
                      [1] + [float(r["gflops_per_gpu"]) * int(r["ranks"]) / baseline for r in rows],
                      color=color, marker=marker, linestyle=style, label=label, markersize=4)
        jobs = defaultdict(list)
        for r in trials:
            if r["matrix"] == matrix and r["backend"] == "acg-cg-mpi" and r["status"] == "valid":
                jobs[(int(r["ranks"]), r["job"])].append(float(r["solver_s"]))
        for ranks in (2, 4, 8, 16, 32):
            selected = [v for (p, _), v in sorted(jobs.items()) if p == ranks]
            for offset, times in zip((-0.06, 0, 0.06), selected):
                median = stats.median(times)
                right.errorbar(ranks * 2**offset, median, yerr=[[median - min(times)], [max(times) - median]],
                               fmt="o", color="#2878b5", markersize=4, capsize=2)
        left.set(title=f"{matrix}: work-normalized scaling", ylabel="Throughput / one-GPU reference")
        right.set(title=f"{matrix}: MPI allocation variability", ylabel="Solver time (s)")
        for ax in (left, right):
            ax.set_xscale("log", base=2)
            ax.set_yscale("log", base=2 if ax is left else 10)
            ticks = [1, 2, 4, 8, 16, 32] if ax is left else [2, 4, 8, 16, 32]
            ax.set_xticks(ticks, [str(n) for n in ticks])
            ax.set_xlabel("GPUs")
            frame(ax)
    axes[0, 0].legend(fontsize=7)
    save(fig, "acg-campaign-summary.png")

    # The SYCL solver comparison is rendered by tools/plot_acg_sycl.py.

    # Device-initiated cg_step against the host implementations, same snapshot.
    cgd = read("cg-device-summary.csv")
    order = ("cuda_mpi", "cuda_nccl", "cuda_nvshmem", "oshmpi", "sycl_mpi", "sycl_oneccl")
    # Multi-rank topologies only: at 1n1g the step involves no communication.
    ranks = {"1n2g": 2, "1n4g": 4, "2n4g": 8, "4n4g": 16, "8n4g": 32}
    fig, axes = plt.subplots(1, 2, figsize=(9.5, 3.8), layout="constrained")
    for ax, side in zip(axes, ("512", "8192")):
        for backend in order:
            label, color, marker = SERIES[backend]
            pts = sorted(((ranks[r["topology"]], float(r["median_us"])) for r in cgd
                          if r["backend"] == backend and r["side"] == side and r["topology"] in ranks),
                         key=lambda x: x[0])
            ax.plot([x for x, _ in pts], [y for _, y in pts], color=color, marker=marker,
                    markersize=3, linewidth=1.1, alpha=0.75, label=label)
        pts = sorted(((ranks[r["topology"]], float(r["median_us"]), float(r["job_min_us"]), float(r["job_max_us"]))
                      for r in cgd if r["backend"] == "cuda_nvshmem_device" and r["side"] == side
                      and r["topology"] in ranks), key=lambda x: x[0])
        xs = [x[0] for x in pts]
        ax.plot(xs, [x[1] for x in pts], color="black", marker="o", markersize=5, linewidth=2.0,
                label="NVSHMEM, device-initiated")
        ax.fill_between(xs, [x[2] for x in pts], [x[3] for x in pts], color="black", alpha=0.12)
        ax.set_xscale("log", base=2)
        ax.set_yscale("log", base=10)
        ax.set_xticks([2, 4, 8, 16, 32], ["2", "4", "8", "16", "32"])
        ax.set(title=f"Global side {side}", xlabel="GPUs", ylabel="Step time (µs)")
        frame(ax)
    axes[0].legend(fontsize=7)
    save(fig, "cg-device-step.png")

    # Device-initiated cg_step against the device solver, both normalized to 2 GPUs.
    dev = read("cg-device-correlation.csv")
    ranks = (2, 4, 8, 16, 32)
    fig, axes = plt.subplots(1, 2, figsize=(9.5, 3.8), layout="constrained")
    for ax, matrix in zip(axes, ("Bump_2911", "Queen_4147")):
        rows = [r for r in dev if r["matrix"] == matrix]
        solver = {int(r["ranks"]): float(r["iteration_normalized"]) for r in rows}
        ax.plot(ranks, [solver[p] for p in ranks], color="black", marker="o", linewidth=1.8,
                label="aCG, device NVSHMEM")
        for side, color in (("512", "#c0392b"), ("2048", "#b48a00"), ("8192", "#2878b5")):
            step = {int(r["ranks"]): float(r["step_normalized"]) for r in rows if r["side"] == side}
            if len(step) < len(ranks):
                continue
            ax.plot(ranks, [step[p] for p in ranks], color=color, marker="s", markersize=4,
                    linestyle="--", linewidth=1.3, label=f"cg_step, side {side}")
        ax.set_xscale("log", base=2)
        ax.set_yscale("log", base=10)
        ax.set_xticks(ranks, [str(p) for p in ranks])
        ax.set(title=matrix, xlabel="GPUs", ylabel="Time relative to 2 GPUs")
        frame(ax)
    axes[0].legend(fontsize=7)
    save(fig, "cg-device-scaling.png")

    ucc = read("ucc-paired.csv")
    off_style, on_style = ("UCC off", "#c0392b", "v"), ("UCC on", "#2878b5", "o")
    for operation, xlabel, ticks, tick_labels in (
        ("allreduce", "Input payload (bytes)", [4, 4096, 65536, 16777216],
         ["4 B", "4 KiB", "64 KiB", "16 MiB"]),
        ("alltoall", "Payload per peer (bytes)", [4, 512, 8192, 262144],
         ["4 B", "512 B", "8 KiB", "256 KiB"])):
        fig, axes = plt.subplots(2, 3, figsize=(10.5, 6.0), sharex="col", layout="constrained")
        for column, topology in enumerate(("1n4g", "2n4g", "8n4g")):
            rows = sorted((r for r in ucc if (r["benchmark"], r["topology"], r["backend"])
                           == (operation, topology, "cuda_mpi")), key=lambda r: int(r["bytes"]))
            xs = [int(r["bytes"]) for r in rows]
            off = [float(r["off_us"]) for r in rows]
            on = [float(r["on_us"]) for r in rows]
            ratio = [float(r["off_over_on"]) for r in rows]

            # Top: what each configuration actually costs.
            top = axes[0, column]
            for values, (label, color, marker) in ((off, off_style), (on, on_style)):
                top.plot(xs, values, label=label, color=color, marker=marker,
                         markersize=3.5, linewidth=1.4)
            top.fill_between(xs, off, on, color="#999999", alpha=0.15)
            top.set_yscale("log", base=10)
            top.set(title=topology, ylabel="Latency (µs)")

            # Bottom: the crossover, signed so the winning side is unambiguous.
            bottom = axes[1, column]
            bottom.plot(xs, ratio, color="black", linewidth=1.3, marker="o", markersize=3)
            bottom.fill_between(xs, ratio, 1, where=[r >= 1 for r in ratio],
                                interpolate=True, color="#159870", alpha=0.25, label="UCC faster")
            bottom.fill_between(xs, ratio, 1, where=[r <= 1 for r in ratio],
                                interpolate=True, color="#c0392b", alpha=0.25, label="UCC slower")
            bottom.axhline(1, color="black", linestyle="--", linewidth=0.8)
            bottom.set_yscale("log", base=10)
            bottom.set(xlabel=xlabel, ylabel="Speedup from UCC ($\\times$)")

            for ax in (top, bottom):
                ax.set_xscale("log", base=2)
                ax.set_xticks(ticks, tick_labels)
                frame(ax)
        for ax in axes[:, 0]:
            ax.legend(fontsize=7)
        save(fig, f"ucc-ab-{operation}.png")


if __name__ == "__main__":
    main()
