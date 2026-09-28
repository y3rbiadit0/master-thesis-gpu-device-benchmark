"""Import the MoE dispatch/combine campaign; export it beside the reconciled archive.

The MoE campaign is a later snapshot than the reconciled inputs in
`tools/rebuild_main_evidence.py`, so it is written to its own files and manifest
rather than merged into `benchmark-summary.csv`. That keeps one archive one
snapshot. The aggregation policy is shared: allocation means first, median of
allocation means as the plotted center, and their range as the band.
"""

import argparse
import hashlib
import importlib.util
import json
import re
import statistics as stats
from collections import Counter, defaultdict
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SOURCE = "docs/analysis/data/2. application_benchmark/moe/moe-points.json"
TOPOLOGIES = ("1n1g", "1n2g", "1n4g", "2n1g", "2n4g", "4n4g", "8n4g")
ROUTINGS = ("uniform", "locality80", "hotspot80")
BACKENDS = ("cuda_mpi", "sycl_mpi", "cuda_nccl", "cuda_nvshmem", "oshmpi", "sycl_oneccl")


def load_module(name):
    spec = importlib.util.spec_from_file_location(name, Path(__file__).parent / f"{name}.py")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


evidence = load_module("rebuild_main_evidence")


def ranks_of(topology):
    nodes, gpus = map(int, re.fullmatch(r"(\d+)n(\d+)g", topology).groups())
    return nodes * gpus


def split_case(case):
    """The recorded case field joins the routing name with the hidden size."""
    routing, _, hidden = case.partition(",hidden=")
    if routing not in ROUTINGS or not hidden.isdigit():
        raise ValueError(f"Unrecognized MoE case label: {case!r}")
    return routing, int(hidden)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--benchmark-root", type=Path, required=True)
    parser.add_argument("--output", type=Path, default=ROOT / "data/main-campaign")
    args = parser.parse_args()
    out = args.output
    out.mkdir(parents=True, exist_ok=True)

    path = args.benchmark_root / SOURCE
    raw = path.read_bytes()
    document = json.loads(raw.decode("utf-8"))

    rows, jobs = [], []
    for point in document["points"]:
        if not point.get("valid") or point.get("metric") != "usec":
            continue
        routing, hidden = split_case(point["case"])
        identity = {"topology": point["topology"], "ranks": ranks_of(point["topology"]),
                    "routing": routing, "hidden": hidden, "backend": point["backend"],
                    "tokens_per_rank": point["n"], "useful_bytes": point["bytes"]}
        summary = evidence.job_summary(point["runs"])
        rows.append({**identity, **summary, "stored_mean_us": point["value_mean"],
                     # Useful volume counts dispatch and combine for every token,
                     # including tokens that never leave their source rank.
                     "useful_gbytes_per_s": point["bytes"] / summary["median_us"] / 1000})
        by_job = defaultdict(list)
        for run in point["runs"]:
            by_job[str(run["job"])].append(run["mean"])
        jobs.extend({**identity, "job": job, "trial_count": len(values), "mean_us": stats.mean(values)}
                    for job, values in sorted(by_job.items()))
    if len(rows) != len(TOPOLOGIES) * len(ROUTINGS) * len(BACKENDS):
        raise ValueError(f"Incomplete MoE matrix: {len(rows)} valid cells")
    rows.sort(key=lambda r: (ROUTINGS.index(r["routing"]), r["ranks"], r["topology"], r["backend"]))
    evidence.write_csv(out / "moe-summary.csv", rows)
    evidence.write_csv(out / "moe-jobs.csv", jobs)

    def cell(routing, topology, backend):
        return next(r for r in rows if (r["routing"], r["topology"], r["backend"]) == (routing, topology, backend))

    # Intra-node NVLink against the largest inter-node placement, per routing case.
    table_rows = []
    for backend in BACKENDS:
        values = [cell(routing, topology, backend)["median_us"]
                  for routing in ROUTINGS for topology in ("1n4g", "8n4g")]
        table_rows.append(evidence.NAMES[backend] + " & "
                          + " & ".join(f"{value:.0f}" for value in values) + r"\\")
    evidence.write_table(out / "moe-table.tex", "lrrrrrr", [
        "Stack", r"Uni.\ \texttt{1n4g}", r"Uni.\ \texttt{8n4g}", r"Loc.\ \texttt{1n4g}",
        r"Loc.\ \texttt{8n4g}", r"Hot.\ \texttt{1n4g}", r"Hot.\ \texttt{8n4g}"], table_rows,
        generator="tools/import_moe_evidence.py")

    manifest = {"schema_version": 1,
                "input_repository_revision": evidence.revision(args.benchmark_root),
                "measured_source_revision": None,
                "generated_by_benchmark_at": document.get("generated"),
                "policy": "median of within-allocation trial means; range over allocation means",
                "relation_to_main_campaign": ("later benchmark snapshot than manifest.json; "
                                              "kept in separate files, not merged"),
                "sources": [{"repository": "benchmark", "path": SOURCE,
                             "sha256": hashlib.sha256(raw).hexdigest()}]}
    (out / "moe-manifest.json").write_text(json.dumps(manifest, indent=2) + "\n")
    summary = {"cells": len(rows), "routings": sorted({r["routing"] for r in rows}),
               "allocations_per_cell": dict(Counter(r["n_jobs"] for r in rows)),
               "trials_per_cell": dict(Counter(r["n_trials"] for r in rows)),
               "slowest_stack_per_routing_at_8n4g": {
                   routing: max(BACKENDS, key=lambda b: cell(routing, "8n4g", b)["median_us"])
                   for routing in ROUTINGS},
               "fastest_stack_per_routing_at_8n4g": {
                   routing: min(BACKENDS, key=lambda b: cell(routing, "8n4g", b)["median_us"])
                   for routing in ROUTINGS}}
    print(json.dumps(summary, indent=2))


if __name__ == "__main__":
    main()
