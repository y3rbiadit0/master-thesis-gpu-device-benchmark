# Methodology and Results Revision Plan

## Objective

Reorganize Chapters 3 and 4 into a clear scientific argument: identify promising
communication paths, test them with computation, and determine which predictions
survive in a complete solver. Reconcile the evidence before revising conclusions.
Keep operational identifiers in experiment records rather than the main narrative.

## Findings to Resolve

- The checked-in `gpu-comm-benchmark/docs/analysis/data/2. application_benchmark/cg_step/cg-points.json`
  does not reproduce the thesis claim that OSHMPI wins every multi-rank cell.
  NCCL wins, for example, `1n2g` at sides 512 and 2048 and `1n4g` at side 2048,
  under both stored means and medians of job means. Identify the campaign snapshot
  and apply one explicit aggregation policy.
- Recompute reduction prediction errors: the benchmark correlation report and
  thesis contain slightly different values.
- Current benchmark and aCG sources implement the complete staged OSHMPI
  device-to-host/reduction/host-to-device sequence. The analysis notes explicitly
  say these changes have not been measured on Leonardo. Stored application logs
  represent OSHMPI halos with MPI scalar reductions.
- The CUDA--SYCL comparison report uses medians for both implementations. Its
  policy differs from the primary fastest-trial CUDA campaign, not between the
  two sides of that comparison.
- The SYCL analysis tool leaves CUDA convergence unset but reports only explicit
  true values as converged. Its `0/3` output does not establish three failures.
- Audit UCC statements against the plotted and tabulated exceptions, phase-gap
  percentage denominators, payload/datatype matching, and scaling-agreement claims.

## Source Repositories

- GPU benchmark: `/Users/stormtrooper/Projects/university/gpu-comm-benchmark`
- oneCCL branches: `/Users/stormtrooper/Projects/university/oneCCL-oshmpi`
- Native aCG: `/Users/stormtrooper/Projects/university/aCG-native`
- SYCL aCG: `/Users/stormtrooper/Projects/university/acg-sycl`

## Proposed Chapter 3 Structure

1. Research design and evidence levels: primitive, composite, solver, and RQ mapping.
2. Platform and evaluated configurations: move software versions from Chapter 4;
   define placement, backend roles, and campaign-specific settings once.
3. Measurement and statistical protocol: timing boundaries, warm-up, correctness,
   independent allocations, aggregation, and prediction metrics.
4. Communication patterns and composite step: operation sequences, payload
   conventions, and the work included or omitted by `cg_step`.
5. oneCCL integration and validation: semantic adaptations and validation criteria;
   distinguish completed adapters from the NVSHMEM runtime foundation.
6. Application validation: matrices, fixed partitions, communicator variants,
   convergence, profiling boundaries, and benchmark-to-application pairing.
7. Exploratory NCCL protocol and reproducibility limitations.

### IBGDA and Operational Detail

Rename the availability subsection to “Transport Availability and Verification”.
Describe relevant prerequisites, observed configuration, selected transport, and
the resulting interpretation. Preserve node names, job IDs, and diagnostics in
experiment records. Distinguish evidence of `ibrc` selection from evidence about
why IBGDA was unavailable. Put quantitative tuning findings in Chapter 4 rather
than mixing them into the methodology's configuration description.

## Proposed Chapter 4 Narrative

1. **Which communication paths are promising?** Use ping-pong and halo curves to
   establish startup and steady-state regimes, then reductions and redistribution
   to show operation-dependent rankings. Use UCC as supporting configuration evidence.
2. **What survives composition with computation?** Present complete-step timings,
   phase diagnostics, scalar placement/completion, and CUDA--SYCL execution costs.
   Replace winner-only reporting with relative timings and variability where possible.
3. **What does a common interface cost?** Give RQ2 an explicit integration-results
   subsection: grouped NCCL validation, OSHMPI staging and blocking completion,
   direct/adapted-stack comparisons, and the NVSHMEM foundation's validated scope.
4. **Which predictions survive in aCG?** Lead with complete-solver behavior, then
   explain scalar prediction, irregular halos and overlap, MPI variability,
   monolithic device execution, and supporting SYCL evidence.
5. **What guidance follows?** Summarize observation, supported explanation, and
   implication. Keep newer NCCL measurements as a short exploratory closing section.

Use prediction-versus-observation plots for reductions and separate displays for
MPI variability. Let reconciled data determine the storyline, rather than preserving
an expected winner or an unsupported causal explanation.

## Targeted Experiments

### Priority 1: Matched Scalar Reductions

Question: does staged OSHMPI retain its advantage when the result must be available
to a GPU consumer?

- Use one-double FP64 sums, both copy directions, and GPU-visible completion.
- Compare MPI and staged OpenSHMEM reductions in aCG while keeping the OSHMPI halo fixed.
- Start at `1n4g`, `2n4g`, and `8n4g`.
- Pair variants within allocations and repeat across independent allocations.
- Record source revisions, effective configuration, correctness, operation latency,
  solver time per iteration, and convergence.
- Validate the already implemented source changes before performance runs.

### Priority 2: Irregular Halo Replay

Question: does preserving peer structure and overlap improve application prediction?

- Reuse stored aCG communication matrices after confirming their count convention.
- Measure submission, completion, exposed wait, and combined communication/compute time.
- Begin at a representative multi-node scale, then confirm smaller and larger placements.
- Compare transfer-only and transfer-with-independent-computation schedules.

### Conditional Supporting Controls

- Allocator-only kernels with ordinary versus symmetric allocations and no communication.
- Selected CUDA--SYCL reruns only if matching historical metadata cannot be recovered.
- A matched host/device NVSHMEM experiment if stronger initiation-only causal claims are desired.

New Leonardo measurements require cluster access; preparation and local analysis
must not be represented as executed or validated cluster experiments.

## Execution Order

1. Establish a canonical inventory of datasets, measured source behavior,
   configurations, completion boundaries, and aggregation policies.
2. Recompute headline tables and errors, resolving campaign discrepancies.
3. Reorganize and rewrite Chapters 3 and 4, preserving useful reference labels.
4. Regenerate central figures from the selected data with reproducible scripts.
5. Prepare and, when cluster access is available, validate and run targeted controls.
6. Update dependent thesis summaries and check numerical consistency, citations,
   references, and PDF layout where a TeX toolchain is available.

## Implementation Status

- Completed the canonical import, including allocation-level benchmark summaries,
  507 residual-valid solver records, prediction pairs, source hashes, and directed
  halo replay inputs checked against recorded byte totals.
- Rewrote Chapters 3 and 4 and updated the dependent introduction, abstract,
  related-work, discussion, and conclusion claims.
- Generated table bodies from the selected records, added four central figures,
  and rebuilt the solver and UCC figures.
- Documented operational provenance in `data/experiment-notes.md` and the targeted
  experiments in `experiments/targeted-controls.md`.
- Eight numerical/parser tests and the static TeX/reference/resource checks pass.
  An independent rebuild reproduces all generated evidence files exactly.
- PDF compilation is pending: neither a local TeX toolchain nor a running Docker
  daemon is available in this environment.
- New Leonardo measurements and the halo replay benchmark implementation remain
  pending. The exported replay inputs and the experiment protocol are ready; no
  unmeasured implementation is presented as an executed cluster experiment.
