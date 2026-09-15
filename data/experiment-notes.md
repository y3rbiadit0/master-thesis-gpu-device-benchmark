# Operational provenance and auxiliary controls

Operational identifiers are retained here for tracing source records. They do
not explain performance and are intentionally omitted from the methodology prose.

## IBGDA diagnostic

The pre-revision methodology recorded Leonardo node `lrdn3445`, Slurm job
`55764638`, for the driver-prerequisite inspection. It recorded NVIDIA driver
535.274.02, loaded `nvidia_peermem`, OFED-internal-23.04-1.1.3, four mlx5 interfaces,
no reported `PeerMappingOverride`, and stream memory operations set to zero.

A two-node NVSHMEM information trace identified `ibrc`. The trace establishes the
transport selected in that probe. It does not, by itself, establish why IBGDA
could not be selected, and a parameter absent from a listing must not be treated
as equivalent to a direct measurement of every driver's effective configuration.

These identifiers and observations are retained from the earlier thesis record;
the original diagnostic output is not imported as a new measurement. Version-
specific driver requirements need rechecking before any new GPU-posted experiment.

## Configuration and implementation controls

The benchmark repository's `docs/analysis/resume.md` records the auxiliary rail
comparison, forced Open MPI all-to-all schedules, OSHMPI scalar placement sweep,
queue-wait changes, and NVSHMEM dispatch controls. `acg-correlation.md` documents
the relationship between archived data and current unmeasured source changes.
Their source hashes are included in `main-campaign/manifest.json`.

The retained UCC on/off summaries are independently exported to
`main-campaign/ucc-paired.csv`. Their per-cell means do not provide raw iteration
or allocation distributions from which new confidence intervals could be inferred.
