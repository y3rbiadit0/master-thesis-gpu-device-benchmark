# Missing Experiments and Rerun Priorities

## Purpose

This report separates gaps that require new cluster measurements from issues that
can be resolved by reanalysis or presentation. The priority is determined by how
directly an experiment changes the thesis's conclusions about device invocation,
completion-equivalent comparison, and transfer from benchmarks to aCG.

The detailed protocols for the first two experiments are in
`experiments/targeted-controls.md`. None of the experiments below are part of the
archived results unless explicitly stated.

## Priority 1: Complete FP64 OSHMPI Reduction Round Trip

**Question:** Does the archived OSHMPI `cg_step` advantage remain when each
reduction result is ready for a dependent GPU consumer?

The archived path copies each FP64 operand to host symmetric memory and performs
the OpenSHMEM reduction, but does not include the host-to-device result copy or a
subsequent GPU dependency. It therefore has a different output state from the MPI
and NCCL paths.

### Required comparison

- Run MPI, NCCL, and OSHMPI with two ordered one-double reductions.
- Include device-to-host staging, reduction, host-to-device return, and the event
  or synchronization that makes the result visible to a GPU consumer.
- Add the same dependent consumer operation to every backend.
- Compare `1n4g`, `2n4g`, and `8n4g` first, then expand only if the result changes
  the interpretation.
- In aCG, compare MPI and staged OpenSHMEM scalar reductions while keeping the
  OSHMPI halo, matrix partition, seed, tolerance, and runtime settings fixed.

### Decision rule

- A retained reduction and solver advantage supports the staged path.
- A primitive advantage without a solver improvement identifies an unmatched
  application dependency.
- A disappearing advantage shows that the historical completion boundary caused
  part of the reported `cg_step` ranking.

## Priority 2: Irregular aCG Halo Replay

**Question:** Does preserving the application's directed peer graph and overlap
opportunity improve agreement with complete aCG?

The existing regular halo has two fixed neighbors. The aCG partitions contain
asymmetric, rank-dependent exchanges with up to 17 outgoing peers on an
individual rank. The existing replay inputs are in
`data/main-campaign/halo-replay.csv`.

### Required comparison

- Preserve each directed edge and its FP64 element count.
- Compare MPI, grouped NCCL point-to-point, host NVSHMEM, and OSHMPI where the
  required correctness protocol is available.
- Measure transfer-only execution and transfer plus calibrated independent local
  work.
- Record host issue time, total exchange time, local-work time, exposed wait, and
  correctness.
- Start at 16 GPUs, then confirm at 4 and 32 GPUs.

### Decision rule

Success means that the replay explains or narrows the application behavior; it
does not require a speedup. Reproducing MPI's slow states would permit a separate
progress and transport investigation.

## Priority 3: Matched NVSHMEM Invocation Experiment

**Question:** How much of the persistent NVSHMEM result is attributable to device
invocation rather than batching, persistence, memory, or protocol differences?

### Required variants

1. Host-called NVSHMEM.
2. Host-enqueued `nvshmemx_*_on_stream` communication.
3. Nonpersistent device-invoked NVSHMEM.
4. Persistent device-invoked NVSHMEM.

Hold message layout, symmetric allocation, transport, signaling, batch length,
operation scope, and device-consumer-ready completion fixed. Report any remaining
algorithmic or execution-organization difference.

This experiment is required for an initiation-only claim. Without it, the thesis
must describe the result as performance of a complete persistent NVSHMEM path.

## Priority 4: Persistence and Batch-Length Sweep

**Question:** Is the favorable steady-halo regime available at application-like
batch lengths?

Sweep at least 1, 2, 4, 8, 16, 32, 64, and 100 exchanges for matched host and
device paths. Report total batch time and amortized per-exchange time. Add an
interleaved halo--compute--reduction schedule so that the result is not limited to
100 consecutive identical exchanges.

## Priority 5: Matched Host and Device aCG Organization

**Question:** Does the device solver's larger-scale behavior come from invocation,
kernel fusion, fewer host synchronizations, or a changed solver schedule?

Use host NVSHMEM as the primary baseline and match the halo protocol, collective
dispatch, numerical recurrence, partition, compute kernels, stopping test, and
completion boundaries. Add launch-only and persistent-compute-only controls where
possible. Standard and pipelined CG should be reported separately.

## Required Configuration Repairs

These runs are narrower than the five experiments above but are required before
the corresponding comparisons are treated as configuration matched.

| Repair | Required action | Result affected |
|---|---|---|
| NVSHMEM collective dispatch | Run benchmark and aCG reductions with the same NCCL-dispatch setting | Scalar-cost agreement |
| CUDA--SYCL correctness | Reprocess original logs with common residual and error criteria; rerun unresolved cells | Performance-retention claim |
| MPI variability | Use the irregular replay first; rerun solver cells only if the replay cannot reproduce the slow mode | Representative scaling |
| All-to-all provenance | Repeat one homogeneous campaign only if small cross-backend rankings remain a thesis claim | Small-message ranking |

## Conditional Experiments

### Verified GPU-Posted Networking

Repeat the matched NVSHMEM experiment on a system with a verified active IBGDA or
equivalent GPU-posted transport. The Leonardo `ibrc` measurements exercise
device-side invocation with CPU-proxy-assisted network progress and cannot answer
this question.

### NCCL 2.31 Device API and Symmetric Memory

Repeat the preliminary study only after recording exact source revision, datatype,
allocation and registration steps, invocation mode, completion boundary,
correctness, warm-up, and individual trials. Start with a one-double intra-node
allreduce. Move to `cg_step` or aCG only if the gain survives that matched test.

### Application-Level All-to-All

A variable-count MoE or redistribution workload is needed before the standalone
all-to-all results are generalized to application selection. This is outside the
core CG evidence chain.

## Reanalysis and Presentation Only

The following work does not require new measurements:

- Present all measured backends for each microbenchmark.
- Recompute and label allreduce bus bandwidth consistently.
- Plot all-to-all against bytes per peer rather than aggregate per-rank bytes.
- Aggregate distribution plots at the allocation level rather than showing one
  box per trial under a job-level label.
- Make median or allocation-level solver performance primary and retain fastest
  trials as a reference-study sensitivity view.
- Label the archived OSHMPI `cg_step` path as host-result-terminal rather than
  solver-ready.
- Treat the 7.8--11.1% MAPE result as cross-level scalar-cost agreement rather
  than held-out prediction accuracy.

## Minimum Thesis Decision

If no new measurements are possible, the main conclusion must remain at the
configured-path level: persistent kernel-invoked, CPU-proxy-assisted NVSHMEM is
favorable for sustained batched regular halo communication on Leonardo, but the
campaign does not isolate an initiation-only benefit or GPU-posted networking.

If cluster time is available, Priorities 1 and 2 resolve the largest
benchmark-to-application gaps. Priorities 3 and 4 are necessary to make device
initiation, rather than the complete persistent implementation, the causal focus
of the thesis.
