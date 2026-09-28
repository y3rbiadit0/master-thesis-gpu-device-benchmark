"""Import the SYCL aCG campaign, paired with native runs from the same allocations.

The campaign runs the SYCL solver and the native CUDA solver in the same jobs,
interleaved round by round with alternating order, on the same matrices, METIS
partitions, manufactured solution, seed, tolerance, 10 warmup iterations, HPC-X
installation, and Open MPI/UCX settings. Three pairs are formed, each changing
the implementation and as little else as the two code bases allow:

    single GPU   acg-cg-single  vs acg-sycl-single       no inter-rank transfer
    MPI          acg-cg-mpi     vs acg-sycl-mpi          MPI halo, MPI sums
    NCCL         acg-cg-nccl    vs acg-sycl-oneccl-nccl  sums through NCCL; the
                                                         SYCL halo stays on MPI

The paired comparison is primary: per allocation, the ratio of the SYCL and
native medians; per cell, the median of those ratios over allocations. The
native main campaign (acg-trials.csv, other allocations and dates) is kept as a
secondary reference.

Both solver times cover the same interval: after warmup, from a barrier through
the initial residual and the iteration loop, maximum over ranks (SYCL
`solver_max_s`, native `total solver time`). Native runs are labelled from the
`--comm` argument recorded in their log rather than from their directory.
"""

import argparse
import csv
import hashlib
import importlib.util
import json
import re
import statistics as stats
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
MATRICES = ("Bump_2911", "Queen_4147")
PAIRS = (("single", "acg-cg-single", "acg-sycl-single"),
         ("mpi", "acg-cg-mpi", "acg-sycl-mpi"),
         ("nccl", "acg-cg-nccl", "acg-sycl-oneccl-nccl"))
LOG_NAME = re.compile(r"-(\d+)-nodes-(\d+)-procs-(\d+)-(\d+)-(stdout|stderr)\.txt$")
FLOAT = r"[+-]?(?:\d+(?:\.\d*)?|\.\d+)(?:[eE][+-]?\d+)?"
WAITS = ("pack", "halo", "allreduce", "readback")


def load_module(name):
    spec = importlib.util.spec_from_file_location(name, Path(__file__).parent / f"{name}.py")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


evidence = load_module("rebuild_main_evidence")


def field(text, line, name):
    """`name=value` on the first line starting with `line:`."""
    match = re.search(r"^" + line + r": .*?\b" + name + r"=(" + FLOAT + r")", text, re.M)
    return float(match.group(1)) if match else None


def parse_sycl(stdout, stderr):
    """Classify a SYCL run with the same status classes as the native parser."""
    exit_status = evidence.number(stderr, r"^\s*Exit status:")
    converged = re.search(r"^solver: .*?\bconverged=(true|false)", stdout, re.M)
    time = field(stdout, "timing", "solver_max_s")
    iterations = field(stdout, "solver", "iterations")
    residual = field(stdout, "validation", "true_rel_residual")
    tolerance = field(stdout, "stopping", "residual_rtol")
    if (exit_status is not None and exit_status != 0) or (converged and converged.group(1) == "false"):
        status = "failed"
    elif time is None or iterations is None or time <= 0 or iterations <= 0:
        status = "incomplete"
    elif residual is None or tolerance is None:
        status = "unknown_correctness"
    elif residual <= tolerance:
        status = "valid"
    else:
        status = "residual_failed"
    record = {"status": status, "solver_s": time, "iterations": iterations,
              "relative_residual": residual, "recurrence_residual": field(stdout, "solver", "rel_residual_r0"),
              "tolerance": tolerance, "error_norm": field(stdout, "solver", "relative_error"),
              "iteration_us": time / iterations * 1e6 if time and iterations else None,
              "index_bits": field(stdout, "solver", "spmv_index_bits")}
    for wait in WAITS:
        record[wait + "_s"] = field(stdout, "waits", wait + "_s")
    return record


def native_label(text):
    comm = re.search(r"--comm (\w+)", text)
    if not comm:
        return None
    return "acg-cg-single" if comm.group(1) == "none" else f"acg-cg-{comm.group(1)}"


def read_runs(root, pattern, parse):
    """(record, source) for every promoted log under root matching pattern."""
    runs = []
    for path in sorted(root.glob(pattern)):
        match = LOG_NAME.search(path.name)
        if not match:
            raise ValueError(f"Unrecognized result filename: {path}")
        nodes, ranks, job, trial = map(int, match.groups()[:4])
        data = path.read_bytes()
        record = parse(path, data.decode("utf-8", "replace"))
        if record is None:
            continue
        source = str(path.relative_to(root.parent))
        runs.append(({"matrix": path.parent.name, "nodes": nodes, "ranks": ranks, "job": job, "trial": trial,
                      "source": source, **record},
                     {"path": source, "sha256": hashlib.sha256(data).hexdigest()}))
    return runs


def parse_sycl_path(path, stdout):
    stderr_path = path.with_name(path.name.replace("-stdout.txt", "-stderr.txt"))
    stderr = stderr_path.read_text(errors="replace") if stderr_path.exists() else ""
    return {"backend": path.parts[-4], **parse_sycl(stdout, stderr)}


def parse_native_path(_, stderr):
    label = native_label(stderr)
    if label not in {cuda for _, cuda, _ in PAIRS}:
        return None
    parsed = evidence.parse_solver(stderr)
    return {"backend": label, **{k: parsed[k] for k in
            ("status", "solver_s", "iterations", "relative_residual", "tolerance", "error_norm", "iteration_us")}}


def median(rows, key):
    return stats.median(float(r[key]) for r in rows)


def allocation_ratios(sycl, native):
    """Per shared job: SYCL median over native median, for time and per iteration."""
    ratios = []
    for job in sorted({r["job"] for r in sycl} & {r["job"] for r in native}):
        s = [r for r in sycl if r["job"] == job]
        n = [r for r in native if r["job"] == job]
        ratios.append((job, median(s, "solver_s") / median(n, "solver_s"),
                       median(s, "iteration_us") / median(n, "iteration_us")))
    return ratios


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--results-root", type=Path, required=True,
                        help="Directory holding the SYCL campaign tree and its paired native tree")
    parser.add_argument("--sycl", default="sycl", help="SYCL campaign tree under the results root")
    parser.add_argument("--paired-native", default="backups-sycl",
                        help="native runs of the same jobs, under the results root")
    parser.add_argument("--output", type=Path, default=ROOT / "data/main-campaign")
    args = parser.parse_args()
    out = args.output

    sycl_runs = read_runs(args.results_root / args.sycl, "acg-sycl-*/suitesparse/*/*-stdout.txt", parse_sycl_path)
    native_runs = read_runs(args.results_root / args.paired_native, "**/suitesparse/*/*-stderr.txt", parse_native_path)
    sycl = [r for r, _ in sycl_runs]
    paired = [r for r, _ in native_runs]
    evidence.write_csv(out / "acg-sycl-trials.csv", sycl)
    evidence.write_csv(out / "acg-sycl-native-trials.csv", paired)

    with (out / "acg-trials.csv").open(newline="") as stream:
        archived = [r for r in csv.DictReader(stream) if r["status"] == "valid"]

    def cell(runs, label, matrix, ranks):
        return [r for r in runs if (r["backend"], r["matrix"], int(r["ranks"])) == (label, matrix, ranks)
                and r["status"] == "valid"]

    rows = []
    for pair, cuda_label, sycl_label in PAIRS:
        for matrix in MATRICES:
            for ranks in sorted({r["ranks"] for r in sycl if (r["backend"], r["matrix"]) == (sycl_label, matrix)}):
                s = cell(sycl, sycl_label, matrix, ranks)
                n = cell(paired, cuda_label, matrix, ranks)
                a = cell(archived, cuda_label, matrix, ranks)
                ratios = allocation_ratios(s, n)
                if not ratios:
                    raise ValueError(f"no paired native runs for {pair} {matrix} {ranks} GPUs")
                rows.append({
                    "pair": pair, "matrix": matrix, "ranks": ranks,
                    "sycl_median_s": median(s, "solver_s"), "sycl_min_s": min(float(r["solver_s"]) for r in s),
                    "sycl_max_s": max(float(r["solver_s"]) for r in s),
                    "sycl_iteration_us": median(s, "iteration_us"), "sycl_iterations": median(s, "iterations"),
                    "native_median_s": median(n, "solver_s"), "native_min_s": min(float(r["solver_s"]) for r in n),
                    "native_max_s": max(float(r["solver_s"]) for r in n),
                    "native_iteration_us": median(n, "iteration_us"), "native_iterations": median(n, "iterations"),
                    "n_allocations": len(ratios), "n_sycl_trials": len(s), "n_native_trials": len(n),
                    "paired_ratio": stats.median(r[1] for r in ratios),
                    "paired_ratio_min": min(r[1] for r in ratios), "paired_ratio_max": max(r[1] for r in ratios),
                    "paired_iteration_ratio": stats.median(r[2] for r in ratios),
                    "archived_median_s": median(a, "solver_s") if a else None,
                    "archived_min_s": min(float(r["solver_s"]) for r in a) if a else None,
                    "archived_ratio": median(s, "solver_s") / median(a, "solver_s") if a else None,
                })
    evidence.write_csv(out / "acg-sycl-comparison.csv", rows)

    def find(pair, matrix, ranks):
        return next((r for r in rows if (r["pair"], r["matrix"], r["ranks"]) == (pair, matrix, ranks)), None)

    def paired_cells(row):
        if row is None:
            return ["--"] * 3
        return [f"{row['native_median_s']:.1f}", f"{row['sycl_median_s']:.1f}", f"${row['paired_ratio']:.2f}$"]

    def grid(cells):
        lines = []
        for matrix in MATRICES:
            for i, ranks in enumerate(sorted({r["ranks"] for r in rows if r["matrix"] == matrix})):
                # The rule between matrices opens the next matrix's first row,
                # since every rendered row must end with a row terminator.
                rule = "\\midrule\n" if i == 0 and matrix != MATRICES[0] else ""
                name = matrix.replace("_", r"\_") if i == 0 else ""
                values = (cells(find("single", matrix, 1)) + ["--"] * 3 if ranks == 1
                          else cells(find("mpi", matrix, ranks)) + cells(find("nccl", matrix, ranks)))
                lines.append(f"{rule}{name} & {ranks} & " + " & ".join(values) + r"\\")
        return lines

    generator = "tools/import_acg_sycl_evidence.py"
    # Paired: native and SYCL medians of the same jobs, and the median over
    # allocations of the per-allocation ratio. At one GPU the single-GPU solvers
    # are compared, in the MPI columns.
    evidence.write_table(out / "acg-sycl-table.tex", "lrrrrrrr",
                         ["Matrix", "GPUs", "MPI", "SYCL MPI", "Ratio", "NCCL", "oneCCL/NCCL", "Ratio"],
                         grid(paired_cells), generator)

    counts = {}
    for label, runs in (("sycl", sycl), ("paired_native", paired)):
        counts[label] = {s: sum(r["status"] == s for r in runs) for s in sorted({r["status"] for r in runs})}
    manifest = {"schema_version": 2,
                "input_repository_revision": evidence.revision(args.results_root),
                "policy": ("per allocation, SYCL median over native median of the same job; per cell, "
                           "median over allocations. Residual-valid trials only. Ratios are SYCL over CUDA; "
                           "above one favors CUDA"),
                "timer": ("SYCL solver_max_s (timing schema 3) and native total solver time: after 10 warmup "
                          "iterations, barrier, initial residual and loop, maximum over ranks"),
                "correctness": "SYCL: host-recomputed ||b - Ax|| / ||b||; native: logged residual over initial residual",
                "pairs": {p: {"cuda": c, "sycl": s} for p, c, s in PAIRS},
                "secondary_reference": "acg-trials.csv (native main campaign)",
                "status_counts": counts,
                "sources": [s for _, s in sycl_runs + native_runs]}
    (out / "acg-sycl-manifest.json").write_text(json.dumps(manifest, indent=2) + "\n")
    print(json.dumps({"status": counts,
                      "cells": [(r["pair"], r["matrix"], r["ranks"], r["n_allocations"], round(r["paired_ratio"], 3),
                                 round(r["paired_iteration_ratio"], 3),
                                 round(r["archived_ratio"], 3) if r["archived_ratio"] else None) for r in rows]}))


if __name__ == "__main__":
    main()
