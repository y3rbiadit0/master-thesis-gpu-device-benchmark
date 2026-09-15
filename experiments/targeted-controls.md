# Targeted controls for benchmark-to-application transfer

Status: **protocol and replay inputs prepared; no new Leonardo runs executed**.
These experiments are separate from the archived results in Chapter 4.

## Common measurement contract

- Record application and dependency revisions, build options, toolkit/driver
  versions, rank-to-GPU/CPU/NIC placement, effective transport and collective
  settings, node allocation, exact command, and trial outcome.
- Compare variants within the same allocation; rotate their order between
  repetitions. Repeat on at least three independent allocations initially.
  More iterations inside one job do not replace independent allocations.
- Retain all valid trial results, errors, timeouts, and failed attempts. Report
  allocation-level centers and ranges before making a winner claim. Increase
  allocations if the apparent difference is comparable with observed variation.
- Separate setup/registration and warm-up from steady-state timing. Report both
  complete-operation and phase costs, with explicit timer boundaries.
- Keep profiling probes separate from performance trials.

## A. Complete FP64 scalar-reduction round trip — first priority

**Question:** does staged OSHMPI retain its advantage when the result must be ready
for a subsequent GPU consumer?

### Source readiness

- The benchmark's `src/shmem/oshmpi/application/cg_step.cu` now copies each staged
  reduction result back to device memory and validates the copy-back.
- Native aCG's `acg/comm.c` implements staged `shmem_double_sum_to_all`; setting
  `ACG_OSHMPI_ALLREDUCE=mpi` selects the earlier MPI path.
- These are implemented candidates, not validated cluster measurements. Build
  and smoke-test both branches before collecting performance data.
- Verify that the timed completion boundary makes the result ready to device
  work for **every** backend. If a consumer kernel is added to the benchmark,
  add the same dependency and work to every compared implementation.

### Minimal matrix

1. Validate on one node before using multi-node allocations.
2. Compare `1n4g`, `2n4g`, and `8n4g` initially.
3. Use one FP64 sum per operation and two ordered operations per composite step.
4. Compare MPI, NCCL, and complete-round-trip OSHMPI in the benchmark. Add NVSHMEM
   only with its collective-dispatch setting explicitly matched to the solver.
5. For aCG, compare `ACG_OSHMPI_ALLREDUCE=mpi` with the staged path while keeping
   the OSHMPI halo, matrix partition, seed, tolerance, and other runtime settings fixed.
6. Start with Bump_2911 and confirm the result with Queen_4147.

The old no-return-copy benchmark is an explicitly labeled historical boundary,
not a competing solver-ready path. Do not pool its samples with the corrected run.

### Measurements and interpretation

Record device-ready reduction latency, device-to-host and host-to-device costs,
collective time, synchronization time, complete step time, solver time, iteration
count, residual ratio, and manufactured-solution error. Separate-pass phase timers
must not be subtracted to claim a measured overlap fraction.

- A persistent reduction gain and corresponding solver gain support adoption.
- A reduction gain without solver improvement identifies an application dependency
  or cost outside the isolated primitive; it is still informative.
- A disappearing gain shows that the old completion boundary explained part of
  the apparent advantage. Update the conclusion rather than selecting only
  favorable payloads or trials.

## B. Irregular halo replay — second priority

**Question:** does preserving the application's peer graph and overlap opportunity
improve prediction compared with a regular ring?

### Prepared input

`data/main-campaign/halo-replay.csv` contains directed FP64 element counts and
byte counts from the stored aCG communication matrices for both matrices at
2, 4, 8, 16, and 32 ranks. The importer checks byte counts against stderr totals.
`halo-signatures.csv` summarizes the degree and outgoing volume distributions.

### Implementation required

Add a replay case to the benchmark that accepts `(source, destination, count)`
edges, packs deterministic rank/iteration-dependent data, and checks each received
segment. Preserve asymmetric counts and zero-degree peers; do not symmetrize the
graph or replace its messages with one equal-sized message per neighbor.

Implement MPI, NCCL grouped point-to-point, and the existing blocking OSHMPI
protocol first. A nonblocking OSHMPI variant requires separately validated remote
completion, notification, and safe reuse; moving `quiet` alone is not sufficient.

### Minimal experiment

- Start at 16 GPUs, where the MPI application variability is pronounced; confirm
  at four and 32 GPUs if the replay reproduces a relevant effect.
- Hold graph, message counts, rank placement, datatype, transport thresholds,
  and correctness contract fixed across backends.
- Compare transfer-only execution with transfer plus independent local work.
  Calibrate that work from the relevant aCG local SpMV interval rather than
  selecting a delay that maximizes a preferred backend's apparent overlap.
- Record host issue time, total exchange interval, local-work time, and exposed
  wait. Include a no-transfer compute control to detect resource contention.
- If an overlapped begin/end path is introduced, ensure the send/receive buffers
  remain valid and are not reused until both local and remote dependencies permit it.

Success is improved explanation or prediction under the application signature,
not necessarily a speedup. Reproducing slow MPI states would enable separate
transport/progress diagnosis; failure to reproduce them narrows the conditions
under which the full solver's behavior occurs.

## Conditional controls

### Allocator-only kernel

Run an identical dot kernel with ordinary and OSHMPI symmetric device output
allocations, with no inter-rank operations. Keep runtime initialization, launch
shape, synchronization, and input data fixed. This tests the reported compute
penalty without changing allocator, residency, and UCC together.

### CUDA--SYCL comparison

Recover the original comparison logs, parse the initial residual, final residual,
tolerances and exit status on both sides, and represent missing values as unknown.
The existing report's CUDA `0/3 converged` field is not evidence of three failures.
Use matched median policies, problem partitions, initial conditions, and timing
boundaries. Rerun selected cells only if the archived comparison cannot be verified.

### Matched initiation experiment

If the thesis claims an initiation-only benefit, compare host-on-stream and
device-invoked NVSHMEM with matched message layout, batch length, transport,
symmetric storage, and completion contract. Report remaining algorithm or
execution-organization differences. This is optional for the current stack-level RQ1.

## Cluster execution boundary

Use the benchmark and aCG repositories' Leonardo build and job entry points.
The existing benchmark launcher's `--explain`/`--dry-run` modes can inspect a
configuration before submission. Separate launcher invocations do not guarantee
paired allocations: implement the paired variants inside one allocation-level
job script. No submission script is claimed to be validated by this protocol.
