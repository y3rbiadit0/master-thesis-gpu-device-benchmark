# Reconciled main-campaign evidence

This is a reanalysis of archived Leonardo measurements, not a new GPU campaign.
The imported archive is selected explicitly rather than combining values from
successive analysis notes. The original inputs remain in the benchmark and native
aCG repositories; `manifest.json` records their relative paths and SHA-256 hashes.
The repository revisions in that manifest identify the imported archive. They are
**not asserted to be the source revisions used for the measurements**.

## Reproduction

From the thesis repository, supply the local source repository paths:

```sh
python3 -B tools/rebuild_main_evidence.py \
  --benchmark-root /path/to/gpu-comm-benchmark \
  --acg-root /path/to/aCG-native \
  --retain cg_step
python3 -B tools/import_moe_evidence.py --benchmark-root /path/to/gpu-comm-benchmark
python3 -B tools/import_acg_sycl_evidence.py \
  --results-root /path/to/gpu-comm-benchmark/docs/analysis/data/acg-results
uv run --no-project tools/plot_main_evidence.py
python3 -B -m unittest discover -s tools/tests -v
```

**Mixed snapshot.** `manifest.json` records `retained_patterns` and marks each
retained source with `retained_from_previous_import`. The current archive mixes
two benchmark snapshots deliberately:

| Pattern | Source |
| --- | --- |
| pingpong, halo_1d, alltoall, UCC | inputs hash-identical to the original import |
| allreduce | re-run exported 2026-09-16 as `all-reducepoints.json`; every cell differs from the original import |
| cg_step | retained from the original import via `--retain` |

`--retain PATTERN` keeps a pattern's rows from the existing CSVs instead of
re-importing it, and carries its original hash forward into the manifest.
`check_snapshot` refuses, before writing anything, an input that would narrow the
archive: a `cg_step` side set smaller than 512/1024/2048/4096/8192, or an
unexpected pattern label. Both refusals correspond to defects seen in real
imported snapshots — the narrowed `cg_step` re-run, and one `sycl_oneccl_oshmpi`
record exported with `benchmark: "step"` instead of `"cg_step"`.

**Snapshot warning.** `rebuild_main_evidence.py` reproduces the archived all-to-all
and `cg_step` summaries only against the benchmark snapshot hashed in
`manifest.json`. The benchmark repository has since replaced
`cg-points.json` with a narrower re-run (side 512 only, five allocations, seven
backends), which does not contain the five-side sweep the `cg_step` tables and
figures are built from. Re-running the import against a newer checkout will
silently shrink that evidence. The exported CSV files in this directory, not the
sibling source tree, are the retained evidence for those two patterns.

The import uses Python's standard library. The plotting script pins Matplotlib
through inline dependency metadata. It reads only the exported CSV files, so
rendering the main figures does not require the sibling repositories.

## Files and statistical meaning

- `benchmark-summary.csv`: one valid pattern/backend/placement/size/case cell.
  `median_us` is the median of allocation means; each allocation mean averages its
  trial means. `job_min_us` and `job_max_us` bracket allocation means, not iterations.
- `benchmark-jobs.csv`: the allocation means underlying those centers and ranges.
  Job IDs belong here as grouping keys, not in the thesis's explanation of results.
- `phase_*_us`: phase means as stored in the input JSON. Per-allocation phase
  samples are unavailable. Phase tables compare these with `stored_mean_us`, not
  the headline median. The phase-sum gap is not a measurement of overlap.
- `ucc-paired.csv`: matched UCC on/off summary means. `bytes` converts the supplied
  float32 count to bytes (per peer for all-to-all). No uncertainty is reconstructed.
- `acg-trials.csv`: completed stderr records from the six named main-campaign
  directories. Validity requires the reported residual criterion; unknown fields
  are not classified as convergence. Partial `.tmp` files are not completed trials.
- `acg-summary.csv`: fastest residual-valid trial per matrix/backend/rank count,
  plus median, maximum, and sample counts. Analytical throughput follows the
  standard-CG formula documented in Chapter 3; it is distinct from the application's
  printed FLOP-rate convention.
- `reduction-predictions.csv`: half the stored side-512 composite reduction phase
  versus accumulated aCG allreduce seconds divided by its recorded call count.
  MPI uses the OSHMPI-halo solver's MPI reductions. NCCL uses the NCCL solver.
- `cg-winners.csv`: lowest median point estimates and their runner-up ratios.
  Winner labels do not establish statistical significance.
- `moe-summary.csv`, `moe-jobs.csv`, `moe-table.tex`, `moe-manifest.json`: the MoE
  dispatch/combine campaign, imported by `tools/import_moe_evidence.py`. Same
  aggregation policy as `benchmark-summary.csv`, deliberately separate files: the
  MoE snapshot is later than the inputs recorded in `manifest.json`, and merging
  them would put two snapshots in one archive. `useful_bytes` is application
  volume for dispatch and combine including tokens that never leave their source
  rank, so `useful_gbytes_per_s` is not a link rate.
- `adapter-comparison.csv`: selected direct/adapted-stack comparisons. These also
  change compute interface or operand placement and do not isolate wrapper overhead.
- `halo-replay.csv`: directed communication graphs from the selected OSHMPI-halo
  solver stdout records. Ranks are zero-based; graph weights count FP64 elements.
  Multiplication by eight is checked against each rank's stderr send-byte totals.
  These are replay **inputs**, not replay performance measurements.
- `halo-signatures.csv`: mean/max outgoing neighbor count and mean send KiB per
  exchange. Byte volume is one-directional and excludes reductions.
- `*-table.tex`: complete generated `tabular` blocks, including headers and rules.
  Include these inside a `table` float but outside any `tabular` environment;
  row-only `\input` calls can interfere with alignment parsing and file hooks.

## Selection and reconciliation

The benchmark inputs are the four `points.json` files under
`docs/analysis/data/1. microbenchmarks/` and `cg-points.json` under
`docs/analysis/data/2. application_benchmark/cg_step/`.

The aCG input is `acg-results/`, restricted to MPI, NCCL, host NVSHMEM, OSHMPI,
single-GPU, and device NVSHMEM directories. `acg-cg-oshmpi-backup-mpi` is excluded:
it is an alternative archived snapshot, not additional independent replication.
The retained main directories supply 507 completed residual-valid records.

This selection corrects several earlier thesis summaries:

- OSHMPI has the lowest estimate in 25/30 multi-rank CG-step cells; NCCL leads
  five intra-node cells. OSHMPI leads all retained multi-node CG-step cells.
- The regenerated scalar MAPE values are MPI 9.2%/11.1% and NCCL 10.5%/7.8%
  for Bump/Queen. Older notes used different OSHMPI snapshots or selected values.
  The current tables use the exact pairs in `reduction-predictions.csv`.
- Allreduce bus bandwidth is explicitly computed from input bytes and latency
  with the factor `2(P-1)/P`. Earlier tables labeled values as bus bandwidth that
  were close to the unnormalized algorithm-bandwidth values.
- Current benchmark and aCG sources contain complete staged OpenSHMEM round-trip
  changes. The analysis record states that these have not been measured on
  Leonardo. Archived results must not be relabeled as runs of the new code.

## Auxiliary evidence

The source hashes for `docs/analysis/resume.md` and `acg-correlation.md` identify
the records supporting rail-count, scalar-placement, forced-algorithm, and
NVSHMEM dispatch controls. Their prose is not a substitute for raw trial data.
In particular, the reported configuration-matched NVSHMEM 14–21% error is not
reconstructed from the default-dispatch JSON or added to the main parity plot.

The separate SYCL comparison and preliminary NCCL medians have different data
availability and remain outside this archive's primary solver ranking. The SYCL
report uses medians on both sides; its CUDA convergence-count field is incomplete
because the original parser does not populate the convergence flag.

## Inscrive Git import

Figure references use explicit project-root paths such as
`figures/results/pingpong-regimes.png`, so asset discovery does not depend on
interpreting `\graphicspath` inside the style file. Sync the generated table
files and figures together with the chapter. `tools/check_thesis.py` checks these
paths and rejects row-only includes inside table alignments.

## SYCL solver campaign

`import_acg_sycl_evidence.py` imports the separate SYCL aCG campaign and pairs it
with the native trials already in `acg-trials.csv`; it must run after the main
import. `acg-sycl-trials.csv` holds one row per SYCL trial with the same status
classes as the native parser. `acg-sycl-comparison.csv` holds one row per
(pair, matrix, GPU count), with medians over residual-valid trials on both sides.
`time_ratio` (median solver time, the reported comparison), `iteration_ratio`,
and `compute_ratio` are SYCL over CUDA, where compute is the
sum of the gemv, dot, nrm2, axpy, and copy categories. Most SYCL cells come from
a single allocation, so their ranges describe trial-to-trial variation only.
`acg-sycl-manifest.json` records the timer definitions and the SHA-256 of every
imported log.
