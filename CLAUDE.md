# Thesis conventions

## Typographic style

Formal thesis styling: bold is reserved for structure the template controls. Prefer italics
for emphasis, and use them sparingly.

| Element | Style | Example |
| --- | --- | --- |
| Section and subsection titles | Bold, from the template | `\section{Backend Considerations}` |
| Inline emphasis | Italics, sparingly | `this is \emph{particularly important} across nodes` |
| Term introduced for the first time | Italics | `a \emph{campaign} is one complete run` |
| Run-in list labels | Italics | `\item \emph{Timing.} Each trial first runs...` |
| Mathematical variables and concepts | Math italics | `the number of processes $P$` |
| Library and tool names | Normal text | MPI, NCCL, NVSHMEM, oneCCL, CUDA, SYCL |
| Code, commands, environment variables | Monospace | `\texttt{UCX\_RNDV\_SCHEME}`, `\texttt{MPI\_Allreduce}` |
| File, benchmark, and executable names | Monospace | `\texttt{cg\_step}`, `\texttt{matrix.sh}` |
| Topology labels | Monospace | `\texttt{1n4g}`, `\texttt{8n4g}` |
| Figure and table references | Normal text | `Figure~\ref{...}`, `Table~\ref{...}` |
| Captions | Normal text; never bold by hand; always a short list title | `\caption[Peak halo bandwidth]{...}` |
| Acronyms | `\ac{KEY}` at first prose use, plain text after | `\ac{HPC}` renders High Performance Computing (HPC) |
| Repositories and external resources | Cited, never a URL in the text | `\cite{merenda_acg_sycl_2026}` |
| Quotations | Normal text in quotation marks | ``...'' |

No URLs appear in the running text or in footnotes: a repository, dataset, or web
resource gets a `@misc` entry in `references.bib` and is cited like any other source. The
contributed artifacts are `merenda_gpu_comm_benchmark_2026`, `merenda_oneccl_nccl_groups_2026`,
`merenda_oneccl_oshmpi_2026`, `merenda_oneccl_nvshmem_2026`, `merenda_acg_oshmpi_2026`, and
`merenda_acg_sycl_2026`.

Do not use `\textbf` in the chapters. Emphasis boxes are provided by the style file:
`keypoint` (per-benchmark takeaways in Chapter 4), `resultbox` (the main result in
Chapter 6), and `researchquestion` (Chapter 1).

## Writing

- State what was measured and what it does not establish; avoid claims the archive cannot support.
- Prefer numbers from the generated tables in `data/main-campaign/` over restating them by hand.
- Keep a fact in one place. Cross-reference rather than repeat it in another chapter.
- Each benchmark section in Chapter 4 ends with a `keypoint` takeaway naming the backends in
  the same order: MPI, OSHMPI, NVSHMEM, NCCL, the oneCCL adapters, then SYCL.

## Terminology

Defined in Chapter 3 and used consistently:

- *cell*: one (pattern, stack, topology) combination, swept over the payload axis.
- *campaign*: one complete run of a benchmark over all of its cells; the *main campaign* is
  everything reported in Chapter 4.
- *trial*: one process launch inside an allocation. *allocation*: one scheduler job.
- *scaling up*: adding GPUs within a node. *scaling out*: adding nodes.
- Topologies are written `NnGg`, never as a bare rank count.

## Tooling

- `python3 -B tools/check_thesis.py` checks labels, citations, references, inputs, figure
  paths, table cell counts, caption short titles, and acronyms. Run it after editing any `.tex` file.
- Acronyms are listed in `backmatter/acronyms.tex` (printed at the end of the thesis). The
  body expands each acronym once, at its first prose use; headings and captions stay plain.
  Chapter, section, and subsection titles appear in the table of contents and spell acronyms out.
  The abstract may use acronyms freely (`ACRONYM_EXEMPT` in the checker). Product names that are not acronyms belong in
  `NOT_ACRONYMS` in the checker.
- `python3 -B -m unittest discover -s tools/tests` covers the data-import and table-generation
  rules.
- Generated tables under `data/main-campaign/*.tex` are complete `tabular` blocks: include them
  with `\input` inside a `table` float, never inside a `tabular`.
- A PDF build is still required to validate layout; no LaTeX toolchain is installed here.
