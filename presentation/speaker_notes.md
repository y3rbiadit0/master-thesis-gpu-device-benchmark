# Thesis defense — speaker notes

14 main slides · target 14:00 · one-minute buffer before questions.

Slides 15–20 are technical backup slides. Stop the main talk on slide 14.

## 1. GPU-Initiated Communication and Application Scalability

*20 s · start 00:00*

My thesis investigates how communication affects applications distributed across GPUs. I compare communication paths, extend interfaces that expose them, and test whether the benchmark results survive in a complete conjugate gradient solver. The key question is when moving communication into GPU kernels actually helps the application.

Sources:
- main.tex: thesis metadata
- chapters/01-introduction.tex

## 2. Fast GPUs still wait for data

*50 s · start 00:20*

A GPU can execute local work very quickly, but a distributed application must also exchange data. On the left, a simulation divides its domain among GPUs. Each GPU needs values from neighboring partitions, and the algorithm also combines small scalar results across all participants. On the right, a mixture-of-experts model routes tokens to expert submodels held on different GPUs. These workloads have very different communication patterns, yet both can spend critical-path time waiting for data. That waiting is the motivation for looking beyond raw compute speed.

Sources:
- chapters/01-introduction.tex: Motivation
- Hamidouche et al., GPU-Initiated Networking for NCCL, arXiv:2511.15076
- Shen et al., Every Microsecond Matters, arXiv:2607.16100

## 3. Move the call into the kernel

*75 s · start 01:10*

GPU-initiated means that a GPU thread issues the communication operation from inside a kernel. In a conventional host-driven sequence, the CPU submits communication and arranges dependencies between producing and consuming kernels. Efficient host libraries can enqueue work asynchronously; this diagram is conceptual, not a claim that every host call blocks. A persistent implementation keeps repeated compute, communication, and synchronization inside device work. Two distinctions are essential. First, GPU-aware MPI can accept a device buffer without allowing a GPU thread to call MPI. Second, a GPU-issued request can still be handed to a CPU proxy for network posting. Direct GPU-memory data movement and direct GPU-to-NIC request posting are separate properties. The CPU also remains responsible for initialization and resource setup.

Sources:
- chapters/02-background.tex
- chapters/04-methodology.tex: NVSHMEM network posting

## 4. Why the interest now?

*50 s · start 02:25*

The interest is driven by a combination of workloads and interfaces. During distributed inference, small collectives can lie directly on the token-generation critical path. Mixture-of-experts models also create routing-dependent exchanges that benefit from fine-grained control. At the same time, symmetric-memory runtimes and device-callable APIs make it practical to combine communication with computation. This creates an opportunity to reduce launches, host coordination, and exposed waiting. It does not guarantee a gain: the kernel must still move data, synchronize correctly, and share GPU resources with computation.

Sources:
- Hamidouche et al. (2025), arXiv:2511.15076
- Ma et al. (2026), Demystifying NVSHMEM, arXiv:2606.05951
- Shen et al. (2026), arXiv:2607.16100

## 5. One ecosystem, different contracts

*65 s · start 03:15*

MPI is the portable message-passing reference. GPU-aware MPI accepts device buffers, but the application calls it from the CPU. Traditional NCCL is also submitted from the host, usually on a CUDA stream, with optimized GPU communication kernels underneath. NVSHMEM exposes a symmetric-memory model with host and device operations: the programmer manages remote addressing, notification, and safe reuse. NCCL has recently added a user device API and GPU-Initiated Networking, or GIN. Its direct and proxy networking backends reinforce why invocation and progress must be distinguished. OSHMPI implements OpenSHMEM over MPI; it is not a GPU-initiated path in this study. oneCCL is the common communication interface that I extended, while SYCL is the compute programming model. These are different layers, not interchangeable categories.

Sources:
- chapters/02-background.tex
- NVIDIA, Device-Initiated Communication, current NCCL documentation, accessed 2026-10-06: https://docs.nvidia.com/deeplearning/nccl/user-guide/docs/usage/deviceapi.html
- Main campaign uses NCCL 2.18.5 and NVSHMEM 2.11.0; newer NCCL device APIs are context/future work.

## 6. When does a faster path help?

*35 s · start 04:20*

I organize the work around three questions. First, in which measured configurations does device initiation help? Second, what programming and runtime costs arise when these paths are exposed through a common interface? Third, which benchmark observations transfer to a complete application? The method is bottom-up: start with patterns, add composition, and finally include the solver's real dependencies and convergence.

Sources:
- chapters/01-introduction.tex: Research Questions
- chapters/04-methodology.tex: evaluation design

## 7. What I built and evaluated

*70 s · start 04:55*

The contributions connect measurement, interface engineering, and application validation. First, I built a common CUDA and SYCL benchmark harness covering seven configured stacks, with shared mapping, timing, and validation policies. Second, I extended oneCCL's NCCL backend so group boundaries reach NCCL, enabling mutually dependent batches of sends and receives. Third, I added the benchmarked OSHMPI operations and a separate NVSHMEM runtime foundation. That NVSHMEM adapter validates bootstrap, lifecycle, and symmetric staging, but its public operations remain unsupported and provide no performance results. Fourth, I added an OSHMPI halo communicator to the existing aCG suite. Finally, I implemented a SYCL version of aCG. The published native aCG solver and its device-NVSHMEM variant are the baseline application, not a new solver algorithm invented by this thesis.

Sources:
- chapters/01-introduction.tex: Contributions
- references.bib: merenda_gpu_comm_benchmark_2026; merenda_oneccl_nccl_groups_2026; merenda_oneccl_oshmpi_2026; merenda_oneccl_nvshmem_2026; merenda_acg_oshmpi_2026; merenda_acg_sycl_2026

## 8. Measure complete configured paths

*55 s · start 06:05*

The main campaign runs on Leonardo's Booster partition, up to eight nodes with four A100 GPUs per node. NVLink and the inter-node network are different communication domains. I therefore label placement explicitly: eight-n-four-g means eight nodes and four GPUs per node. The measured NVSHMEM inter-node transport is ibrc, with CPU-proxy request posting; IBGDA was unavailable in this environment. Payloads can still use GPUDirect RDMA. The experiments progress from ping-pong, halos, reductions, and all-to-all through MoE and a composite CG step, then complete aCG solves on Bump and Queen. Comparisons describe configured paths, including their completion rules, rather than a pure change of call location.

Sources:
- chapters/04-methodology.tex: Experimental Setup, NVSHMEM network posting, benchmark protocol
- NVSHMEM collectives dispatch to NCCL in the default benchmark; aCG disables that dispatch.

## 9. Persistence helps regular halos

*75 s · start 07:00*

The clearest favorable device-initiated regime is the steady halo. Here each sample contains one hundred regular neighbor exchanges, and NVSHMEM executes them inside a persistent GPU kernel with neighbor signaling. At eight nodes with four GPUs each, the effective aggregate rate is 40.6 gigabytes per second, compared with 35.7 for CUDA MPI and 24.4 for OSHMPI. The NVSHMEM rate is also nearly flat across the three multi-node placements. This is an aggregate benchmark rate, not the rate of one physical network link. MPI retains the small-message and isolated-exchange advantage. Importantly, the paths differ in batching, signaling, persistence, and completion as well as initiation. The result identifies a useful complete execution path; it does not isolate a GPU-initiation-only speedup.

Sources:
- data/main-campaign/halo_1d-bandwidth-table.tex
- chapters/04-methodology.tex: halo timing, 100-exchange batches
- chapters/06-discussion.tex: Device-Initiated Scaling

## 10. Routing changes the winner

*65 s · start 08:15*

A uniform all-to-all does not describe every routed workload. This chart keeps topology and total useful volume fixed and changes only routing. Values are normalized to MPI within each routing case, so lower is better. Under uniform routing, NCCL takes about half MPI's time. With locality-biased routing, NCCL becomes 1.55 times slower than MPI, while NVSHMEM is favorable. With eighty percent of tokens targeting one rank, the two one-sided put-based paths take about 1.8 times MPI's time. This is a dispatch-and-combine microbenchmark; routing, planning, and packing are outside timing, and there is no end-to-end MoE model result. The lesson is to match the payload distribution, not just the collective name and byte count.

Sources:
- data/main-campaign/moe-table.tex (microseconds; 8n4g columns)
- All six measured stacks, uniform / locality / hotspot: MPI: 6071 / 1513 / 34028; SYCL MPI: 6013 / 1527 / 33945; NCCL: 3038 / 2352 / 39617; NVSHMEM: 5050 / 1086 / 62007; OSHMPI: 10350 / 2561 / 62686; oneCCL/NCCL: 3063 / 1283 / 38924
- chapters/04-methodology.tex: MoE timing and useful-volume definition

## 11. An adapter can change the path

*65 s · start 09:20*

The same common interface can be inexpensive or costly depending on the adaptations it requires. For the bulk all-to-all endpoint, oneCCL over NCCL takes 0.98 times direct NCCL's time: essentially comparable at this resolution. My grouped point-to-point extension preserves the batch structure and asynchronous execution. For a sixteen-mebibyte intra-node allreduce, oneCCL over OSHMPI takes 17.9 times direct OSHMPI's time, about 6.54 milliseconds versus 0.364 milliseconds. Ordinary application buffers must be adapted to symmetric staging and a blocking completion contract. These are two different operation regimes, not a head-to-head ratio between adapters, and the comparisons also change compute interface or operand placement. They demonstrate the cost of the complete adapted path rather than pure wrapper overhead.

Sources:
- data/main-campaign/adapter-comparison.csv
- All-to-all endpoint: bytes_per_rank=8388608; direct 842.339 µs, adapted 824.939333 µs
- Allreduce endpoint: direct 364.465667 µs, adapted 6537.54 µs
- chapters/06-discussion.tex: RQ2

## 12. The solver is the deciding test

*95 s · start 10:25*

The application test solves two large sparse systems with conjugate gradient. Each iteration combines local sparse work, halo exchange, scalar reductions, and a convergence dependency. These charts follow the thesis's representative fastest residual-valid trial per configuration; they are not median curves, and the appendix provides median endpoints as a check. Device-NVSHMEM improves relative to the blocking OSHMPI-halo solver at larger configurations. NCCL nevertheless has lower representative times across these retained curves. At eight nodes, for example, Queen takes 7.25 seconds with NCCL, 8.79 with device-NVSHMEM, and 9.60 with OSHMPI. Bump's NCCL and device-NVSHMEM medians at that endpoint are very close, so I do not interpret that small gap as a robust ordering. The regular benchmark halo does not reproduce the solver's irregular peers and overlap. Matched scalar reductions agree more closely across levels. The meaningful target is exposed application time under the same result and completion requirements, not the fastest isolated transfer.

Sources:
- data/main-campaign/acg-summary.csv: best_solver_s; all plotted paths have 9 trials / 3 allocations per cell
- data/main-campaign/reduction-error-table.tex
- chapters/06-discussion.tex: Cross-Level Synthesis and Limitations
- At 8n4g, Bump medians: NCCL 6.369126 s; device NVSHMEM 6.413378 s.

## 13. What comes next?

*80 s · start 12:00*

Recent interfaces make the next experiments especially relevant. NCCL now offers device communication and GIN, with both GPU-direct request-posting and proxy implementations. Recent work by Shen and colleagues builds low-latency collectives on NCCL's device API and reports overhead within seven percent of its modeled scale-up hardware lower bound. That is a published result in its studied regime, not a result of this thesis or a general scale-out guarantee. My first priority is a matched comparison of proxy and verified GPU-posted networking. Second, isolate initiation from persistence, allocation, batching, algorithm, and completion. Third, strengthen application correspondence by replaying real peer graphs and matching local work. Finally, newer NVSHMEM and NCCL device operations could be exposed through a portable oneCCL and SYCL interface. Every candidate improvement must then be tested in a complete application.

Sources:
- chapters/07-conclusion.tex: five future directions
- NVIDIA current NCCL documentation, accessed 2026-10-06: https://docs.nvidia.com/deeplearning/nccl/user-guide/docs/usage/deviceapi.html
- Hamidouche et al. (2025), arXiv:2511.15076, https://arxiv.org/abs/2511.15076
- Shen et al. (2026), arXiv:2607.16100, https://arxiv.org/abs/2607.16100; scale-up scope

## 14. Choose for the application

*40 s · start 13:20*

The conclusion is that GPU initiation is a conditional tool. It is effective when the traffic structure and execution model let it reduce exposed work, but the call location alone does not determine performance. My contribution is a connected method and set of software paths for testing that decision: match the application's communication pattern, match its completion requirements, and validate the complete solver. Thank you. I am happy to take questions.

Sources:
- chapters/07-conclusion.tex
- Presentation template: Greenwashing Impact Thesis Defense by Slidesgo. Original Thanks-slide attribution retained in the layout.

## 15. Full solver endpoints & protocol

*Backup*

This table exposes the other native backends and the difference between best and median statistics. Native MPI enters a slow mode in several multi-node configurations; the very large best-to-median spread must not be hidden by reporting only a fastest trial. At 8n4g, Bump MPI has eight retained trials; the other listed endpoint cells have nine, all across three allocations. Each solver run uses a manufactured solution and relative residual tolerance 1e-6. Timing covers solver execution, not initialization. Pattern centers are medians of allocation means, with trial means averaged within an allocation. Different backends have documented completion boundaries. The steady halo is a 100-exchange batch, not raw wire latency. NVSHMEM default benchmark collectives dispatch to NCCL; aCG disables that dispatch. The separate SYCL campaign uses NCCL 2.22.3 under oneCCL, unlike the main NCCL 2.18.5 campaign.

Sources:
- data/main-campaign/acg-summary.csv
- data/main-campaign/README.md
- chapters/04-methodology.tex: repetition, aggregation, timing, and aCG protocol

## 16. SYCL can retain native performance

*Backup*

The SYCL study interleaves native and SYCL executions in the same allocations. The reported ratio is the median over allocations of per-allocation ratios of medians, not necessarily the quotient of the two global medians. Across one to four GPUs, the reported ratios are 0.87 to 1.02 for the two matrices. Matching 32-bit sparse indices, device-resident scalars, and one host convergence wait per iteration is important. Across nodes the oneCCL/NCCL path imposes host completion on reductions, and it must not be interpreted as a programming-model-only cost. The paired NCCL comparison also changes library version. The MPI slow mode in the native path is not a universal property of MPI: the SYCL MPI path continues scaling on the same installation. All claims concern the measured NVIDIA platform.

Sources:
- data/main-campaign/acg-sycl-table.tex
- data/main-campaign/acg-sycl-comparison.csv
- chapters/06-discussion.tex: SYCL Portability Cost

## 17. Transfer requires matched dependencies

*Backup*

Two narrowly matched checks support correspondence. The matched MPI and NCCL scalar intervals differ by 7.8 to 11.1 percent on average across five configurations. The device CG-step scaling shape agrees with the monolithic solver at grid side 8192 but differs enormously at side 512, even though the communication sequence and backend are unchanged. Local work per GPU and the work-to-transfer ratio are therefore essential matching variables. The regular two-neighbor benchmark halo does not capture the solver's directed peer graph or its overlap. These are descriptive comparisons, not trained models or held-out predictions. The scalar comparison uses MPI reductions from the OSHMPI-halo solver and reductions from the NCCL solver.

Sources:
- data/main-campaign/reduction-error-table.tex: [['MPI', '9.2\\%', '11.1\\%'], ['NCCL', '10.5\\%', '7.8\\%']]
- data/main-campaign/cg-device-correlation-table.tex: [['512', '582.2\\%', '852.6\\%'], ['1024', '490.2\\%', '723.0\\%'], ['2048', '328.2\\%', '490.7\\%'], ['4096', '56.0\\%', '104.8\\%'], ['8192', '8.0\\%', '12.6\\%']]
- chapters/06-discussion.tex: Cross-Level Synthesis

## 18. Newer NCCL: a follow-up candidate

*Backup*

This exploratory study is outside the main campaign and does not answer the research questions. The eight-byte allreduce median changes from 12.4 to 7.5 microseconds with symmetric allocation and registration in NCCL 2.31.2, but ordinary allocation in the new version remains at 12.6. At 256 KiB the symmetric result is slower. Small all-to-all also does not show the allreduce benefit. The eight-byte payload is not automatically one FP64 sum because datatype is unrecorded. Exact source, launch configuration, completion, warm-up, validation output, and individual trials are unavailable. No uncertainty interval or application speedup can be reconstructed. The next step is a controlled reduction with verified invocation and GPU-consumable completion.

Sources:
- appendices/nccl-preliminary.tex
- NVIDIA NCCL buffer registration and device API documentation

## 19. What the evidence leaves open

*Backup*

The archive characterizes one platform and configured paths. GPU initiation was not varied independently of persistence, batching, signaling, and kernel organization. There are two sparse matrices and no end-to-end MoE application. Sampling uses a small number of independent allocations, without hypothesis tests, so small point differences are not robust rankings. Future experiments should isolate those factors, verify transport selection and GPU/NIC placement, measure equivalent GPU-visible result states, and test complete applications. Portable device communication would need explicit ownership for symmetric windows and device handles without losing the host interface's stream and completion semantics.

Sources:
- chapters/06-discussion.tex: Limitations
- chapters/07-conclusion.tex: Future Work

## 20. Selected sources & artifacts

*Backup*

These references support the background and recent-developments slides. External results are attributed to their authors; the thesis measurements use the retained archive identified in the accompanying manifest. The three recent papers are preprints in the cited arXiv versions. The native aCG baseline is credited in the thesis to Trotter et al. (2025); this thesis extends its communication and compute paths. The presentation is derived from the supplied Slidesgo template, and its original Thanks-slide credits are retained.

Sources:
- https://arxiv.org/abs/2606.05951
- https://arxiv.org/abs/2511.15076
- https://arxiv.org/abs/2607.16100
- https://docs.nvidia.com/deeplearning/nccl/user-guide/docs/usage/deviceapi.html
- references.bib: trotter_cpu-_2025
- merenda_gpu_comm_benchmark_2026: https://github.com/y3rbiadit0/gpu-comm-benchmark
- merenda_oneccl_nccl_groups_2026: https://github.com/y3rbiadit0/oneCCL/tree/fix/nccl_group_support
- merenda_oneccl_oshmpi_2026: https://github.com/y3rbiadit0/oneCCL/tree/feat/oshmpi
- merenda_oneccl_nvshmem_2026: https://github.com/y3rbiadit0/oneCCL/tree/feat/nvshmem_collectives
- merenda_acg_oshmpi_2026: https://github.com/y3rbiadit0/aCG-oshmpi/tree/oshmpi
- merenda_acg_sycl_2026: https://github.com/y3rbiadit0/acg-sycl

