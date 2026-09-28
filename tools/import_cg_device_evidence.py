"""Import the device-initiated CG-step campaign and its agreement with device aCG.

The device-initiated \\texttt{cg\\_step} stack is a later snapshot than the
reconciled inputs, so it is written to its own files, like the MoE campaign.
Neither the device benchmark nor the monolithic device solver records phase
timers, so the two levels are compared on whole-iteration time instead of on the
reduction phase: the benchmark's step time against the solver's time per
iteration, normalized to the two-GPU value of each series so that a difference
in problem size does not enter the comparison.
"""

import argparse
import hashlib
import importlib.util
import json
import statistics as stats
from collections import Counter, defaultdict
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SOURCE = "docs/analysis/data/2. application_benchmark/cg_step_device/cg_step_points.json"
DEVICE = "cuda_nvshmem_device"
RANK_TOPOLOGY = {2: "1n2g", 4: "1n4g", 8: "2n4g", 16: "4n4g", 32: "8n4g"}
RANKS = tuple(RANK_TOPOLOGY)
MATRICES = ("Bump_2911", "Queen_4147")


def load_module(name):
    spec = importlib.util.spec_from_file_location(name, Path(__file__).parent / f"{name}.py")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


evidence = load_module("rebuild_main_evidence")


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--benchmark-root", type=Path, required=True)
    parser.add_argument("--output", type=Path, default=ROOT / "data/main-campaign")
    args = parser.parse_args()
    out = args.output

    raw = (args.benchmark_root / SOURCE).read_bytes()
    document = json.loads(raw.decode("utf-8"))

    rows, jobs = [], []
    for point in document["points"]:
        if not point.get("valid") or point.get("metric") != "usec":
            continue
        if point.get("benchmark") != "cg_step":
            # The exporter mislabels some records; they are reported, not imported.
            print(f"skipping mislabeled record: {point['benchmark']!r} {point['backend']} {point['topology']}")
            continue
        identity = {"backend": point["backend"], "topology": point["topology"], "side": point["n"]}
        summary = evidence.job_summary(point["runs"])
        rows.append({**identity, **summary, "stored_mean_us": point["value_mean"]})
        by_job = defaultdict(list)
        for run in point["runs"]:
            by_job[str(run["job"])].append(run["mean"])
        jobs.extend({**identity, "job": job, "trial_count": len(v), "mean_us": stats.mean(v)}
                    for job, v in sorted(by_job.items()))
    rows.sort(key=lambda r: (r["backend"], r["side"], r["topology"]))
    evidence.write_csv(out / "cg-device-summary.csv", rows)
    evidence.write_csv(out / "cg-device-jobs.csv", jobs)

    step = {(r["topology"], r["side"]): r["median_us"] for r in rows if r["backend"] == DEVICE}
    with (out / "acg-summary.csv").open(newline="") as stream:
        import csv
        solver = {(r["matrix"], int(r["ranks"])): float(r["best_iteration_us"])
                  for r in csv.DictReader(stream) if r["backend"] == "acg-device-nvshmem"}

    # Strong-scaling shape, each series normalized to its own two-GPU value.
    sides = sorted({r["side"] for r in rows
                    if all((RANK_TOPOLOGY[p], r["side"]) in step for p in RANKS)})
    pairs, errors = [], {}
    for side in sides:
        base = step[(RANK_TOPOLOGY[2], side)]
        for matrix in MATRICES:
            solver_base = solver[(matrix, 2)]
            deviations = []
            for ranks in RANKS:
                predicted = step[(RANK_TOPOLOGY[ranks], side)] / base
                observed = solver[(matrix, ranks)] / solver_base
                deviations.append(abs(predicted / observed - 1))
                pairs.append({"side": side, "matrix": matrix, "ranks": ranks,
                              "step_us": step[(RANK_TOPOLOGY[ranks], side)],
                              "iteration_us": solver[(matrix, ranks)],
                              "step_normalized": predicted, "iteration_normalized": observed,
                              "absolute_relative_error": deviations[-1]})
            errors[(side, matrix)] = 100 * stats.mean(deviations)
    evidence.write_csv(out / "cg-device-correlation.csv", pairs)
    evidence.write_table(out / "cg-device-correlation-table.tex", "rrr",
        ["Grid side", r"Bump\_2911", r"Queen\_4147"],
        (f"{side} & {errors[(side, 'Bump_2911')]:.1f}\\% & {errors[(side, 'Queen_4147')]:.1f}\\%" + r"\\"
         for side in sides), generator="tools/import_cg_device_evidence.py")

    manifest = {"schema_version": 1,
                "input_repository_revision": evidence.revision(args.benchmark_root),
                "generated_by_benchmark_at": document.get("generated"),
                "policy": "median of within-allocation trial means; range over allocation means",
                "comparison": ("device cg_step step time against device aCG time per iteration, "
                               "each normalized to its own two-GPU value; neither level records "
                               "phase timers, so no reduction-level comparison is possible"),
                "relation_to_main_campaign": "later benchmark snapshot; kept in separate files",
                "sources": [{"repository": "benchmark", "path": SOURCE,
                             "sha256": hashlib.sha256(raw).hexdigest()}]}
    (out / "cg-device-manifest.json").write_text(json.dumps(manifest, indent=2) + "\n")
    print(json.dumps({"cells": len(rows),
                      "allocations_per_cell": {b: dict(Counter(r["n_jobs"] for r in rows if r["backend"] == b))
                                               for b in sorted({r["benchmark"] if False else r["backend"] for r in rows})},
                      "complete_scaling_sides": sides,
                      "mape_percent": {f"{s}/{m}": round(e, 1) for (s, m), e in errors.items()}},
                     indent=2))


if __name__ == "__main__":
    main()
