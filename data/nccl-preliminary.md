# Preliminary NCCL comparison: provenance and rendering

`nccl-preliminary.csv` transcribes all 21 allreduce and 19 all-to-all rows
from the author-supplied workspace note `GDAKI) Results`, inspected on
2026-09-11. It contains **summary medians**, not raw observations. Each cell
is described by the note as the median of three runs on one Leonardo Booster
node with four NVIDIA A100 GPUs.

## Configuration labels

- `nccl_2_18_5_us`: NVHPC 24.5 module NCCL 2.18.5, plain `cudaMalloc`.
- `nccl_2_31_2_plain_us`: NCCL 2.31.2, plain `cudaMalloc`.
- `nccl_2_31_2_symmetric_us`: NCCL 2.31.2, `ncclMemAlloc` and symmetric
  window registration. The note calls this “LSA”; the timing summary alone
  does not establish host-called versus custom device-API execution.

The original note reports a 1.5-fold spread for the 4 B plain-2.31 allreduce
cell, attributed there to warm-up, and 1.0–1.1-fold spread elsewhere. The
definition of spread and individual trials are unavailable; the plots
therefore retain the anomalous median and do not invent error bars or
confidence intervals. Missing 2/4 KiB allreduce rows are not interpolated
into the CSV. Connecting lines in figures are visual guides only.

`size_bytes` is the supplied size label converted to bytes using binary
units. For all-to-all, the reported 16 MiB bus bandwidth is consistent with
total per-rank buffer size and the `(P-1)/P` factor at P=4; it is not treated
as the main benchmark's per-peer byte axis without the original command
and source revision. Datatype is unspecified: an 8 B cell is **not** evidence
that one FP64 scalar was reduced.

## Missing provenance

Raw logs, job IDs/dates, exact build and launch commands, `nccl-tests` commit,
datatype/reduction operator, process/thread/GPU mapping, in-place mode,
device implementation selector, selected kernel/transport, iteration and
warm-up counts, timing/completion boundary, correctness output, and whether
allocation/registration were excluded from timing remain unverified.
The note's qualitative inter-node proxy regression and GDAKI hangs have no
tabulated timings here. They are not plotted, converted into speedups, or
used to prove a driver-level cause.

## Reproduction

From the repository root:

```sh
uv run tools/plot_nccl_preliminary.py
```

The script pins Matplotlib using inline dependency metadata and emits
`nccl-preliminary-allreduce.png` and `nccl-preliminary-alltoall.png` under
`figures/results/`.
Both figures show all three medians and speedups computed from the rounded
latencies: `reference latency / symmetric latency`; a ratio above one favors
the symmetric configuration. Ratios can differ in the last digit from the
original summary's independently rounded ratio column.

The CSV and this provenance note make the transcription reproducible; they
do not replace the missing experimental records. No new measurements are
created by the plotting script.
