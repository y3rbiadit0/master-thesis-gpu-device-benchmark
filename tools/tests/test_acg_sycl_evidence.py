"""Checks for the SYCL aCG import's log parsing and pairing."""

import csv
import importlib.util
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]


def load(name):
    spec = importlib.util.spec_from_file_location(name, ROOT / "tools" / f"{name}.py")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


sycl = load("import_acg_sycl_evidence")

# The lines the SYCL solver prints (timing schema 3), with another rank's
# diagnostics interleaved, as they appear in real logs.
RUN = """stopping: residual_rtol=1e-06 residual_atol=0 max_iters=100000 warmup=10 manufactured=true
solver_diag_partition: 1 727855 32230800 31860000 370786 32899 32899 32942
solver: converged=true iterations=100 initial_residual=4e+14 residual=3.8e+08 rel_residual_r0=9.5e-07 rel_residual_rhs=9.5e-07 rhs_norm=4e+14 relative_error=0.14 flops=1e+09 gflops=50 solve_time=2s spmv_index_bits=32
timing: schema=3 setup_s=1.000000 warmup_s=0.200000 solver_s=1.900000 solver_max_s=2.000000 solver_min_s=1.800000 per_iter_us=20000.000000 post_solve_s=0.100000 validation_s=0.300000
waits: pack_s=0.050000 halo_s=0.100000 allreduce_s=1.500000 readback_s=0.001000
validation: true_residual=3.800000e+08 true_rel_residual=9.600000e-07 recurrence_rel_residual=9.500000e-07
"""


class SyclImportTests(unittest.TestCase):
    def test_slowest_rank_time_and_waits_are_read(self):
        record = sycl.parse_sycl(RUN, "\tExit status: 0\n")
        self.assertEqual(record["status"], "valid")
        self.assertEqual(record["solver_s"], 2.0)
        self.assertAlmostEqual(record["iteration_us"], 20000.0)
        self.assertEqual((record["pack_s"], record["halo_s"], record["allreduce_s"], record["readback_s"]),
                         (0.05, 0.1, 1.5, 0.001))
        self.assertEqual(record["index_bits"], 32)

    def test_the_host_recomputed_residual_decides_validity(self):
        record = sycl.parse_sycl(RUN, "")
        self.assertEqual(record["relative_residual"], 9.6e-07)
        failing = RUN.replace("true_rel_residual=9.600000e-07", "true_rel_residual=2.000000e-06")
        self.assertEqual(sycl.parse_sycl(failing, "")["status"], "residual_failed")

    def test_nonzero_exit_and_nonconvergence_are_failures(self):
        self.assertEqual(sycl.parse_sycl(RUN, "\tExit status: 1\n")["status"], "failed")
        self.assertEqual(sycl.parse_sycl(RUN.replace("converged=true", "converged=false"), "")["status"], "failed")

    def test_a_log_without_the_timing_line_is_incomplete(self):
        text = "".join(line for line in RUN.splitlines(keepends=True) if not line.startswith("timing:"))
        self.assertEqual(sycl.parse_sycl(text, "")["status"], "incomplete")

    def test_native_runs_are_labelled_from_the_logged_communicator(self):
        command = 'Command being timed: "srun acg-cuda A.mtx --solver acg --comm {}"'
        self.assertEqual(sycl.native_label(command.format("mpi")), "acg-cg-mpi")
        self.assertEqual(sycl.native_label(command.format("nccl")), "acg-cg-nccl")
        self.assertEqual(sycl.native_label(command.format("none")), "acg-cg-single")
        self.assertIsNone(sycl.native_label("no command line"))

    def test_allocation_ratio_pairs_only_shared_jobs(self):
        def run(job, time):
            return {"job": job, "solver_s": time, "iteration_us": time}
        ratios = sycl.allocation_ratios([run(1, 2.0), run(1, 4.0), run(2, 9.0)], [run(1, 3.0), run(3, 1.0)])
        self.assertEqual(ratios, [(1, 1.0, 1.0)])

    def test_every_sycl_cell_is_paired_with_native_runs_of_the_same_jobs(self):
        with (ROOT / "data/main-campaign/acg-sycl-comparison.csv").open(newline="") as stream:
            rows = list(csv.DictReader(stream))
        pairs = {(r["pair"], r["matrix"], r["ranks"]) for r in rows}
        for matrix in sycl.MATRICES:
            self.assertIn(("single", matrix, "1"), pairs)
            for ranks in ("2", "4", "8", "16", "32"):
                self.assertIn(("mpi", matrix, ranks), pairs)
                self.assertIn(("nccl", matrix, ranks), pairs)
        self.assertTrue(all(int(r["n_allocations"]) >= 2 for r in rows))


if __name__ == "__main__":
    unittest.main()
