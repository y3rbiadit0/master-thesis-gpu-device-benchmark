"""Checks for the statistical and parsing distinctions used in the thesis."""

import importlib.util
import unittest
from pathlib import Path

spec = importlib.util.spec_from_file_location("evidence", Path(__file__).parents[1] / "rebuild_main_evidence.py")
evidence = importlib.util.module_from_spec(spec)
spec.loader.exec_module(evidence)

VALID = """
reading matrix: 1 seconds (5 rows, 9 nonzeros)
total iterations: 10
total solver time: 0.5 seconds
allreduce: 0.000044 seconds/proc 22 times/proc 176 B/proc
tolerance for residual: 0
tolerance for relative residual: 1e-6
initial residual 2-norm: 1e12
residual 2-norm: 5e5
Exit status: 0
"""


class EvidenceTests(unittest.TestCase):
    def test_allocations_have_equal_weight_despite_unequal_trials(self):
        runs = [{"job": "a", "mean": 1}] * 10 + [{"job": "b", "mean": 100}, {"job": "c", "mean": 200}]
        result = evidence.job_summary(runs)
        self.assertEqual(result["median_us"], 100)
        self.assertEqual(result["n_jobs"], 3)
        self.assertEqual(result["n_trials"], 12)

    def test_invalid_latency_does_not_enter_statistics(self):
        with self.assertRaises(ValueError):
            evidence.job_summary([{"job": "a", "mean": 0}])

    def test_large_absolute_residual_can_satisfy_relative_tolerance(self):
        result = evidence.parse_solver(VALID)
        self.assertEqual(result["status"], "valid")
        self.assertAlmostEqual(result["relative_residual"], 5e-7)

    def test_missing_correctness_is_unknown_not_failed_or_valid(self):
        result = evidence.parse_solver("total iterations: 10\ntotal solver time: 0.5\nExit status: 0")
        self.assertEqual(result["status"], "unknown_correctness")

    def test_exit_failure_and_residual_failure_are_retained(self):
        self.assertEqual(evidence.parse_solver(VALID.replace("Exit status: 0", "Exit status: 1"))["status"], "failed")
        self.assertEqual(evidence.parse_solver(VALID.replace("residual 2-norm: 5e5", "residual 2-norm: 5e8"))["status"], "residual_failed")

    def test_reduction_uses_recorded_count_including_extra_operations(self):
        result = evidence.parse_solver(VALID)
        self.assertEqual(result["allreduce_calls"], 22)
        self.assertAlmostEqual(result["allreduce_us"], 2)
        self.assertEqual(result["full_nnz"], 13)

    def test_directed_halo_counts_and_fp64_bytes_are_preserved(self):
        edges = evidence.parse_comm_matrix("%%MatrixMarket matrix coordinate integer general\n2 2 2\n1 2 3\n2 1 5\n", 2)
        self.assertEqual(edges, [{"src_rank": 0, "dst_rank": 1, "elements": 3, "bytes": 24},
                                 {"src_rank": 1, "dst_rank": 0, "elements": 5, "bytes": 40}])

    def test_narrower_cg_step_snapshot_is_rejected_before_writing(self):
        narrow = [{"benchmark": "cg_step", "n": 512}]
        with self.assertRaises(SystemExit) as caught:
            evidence.check_snapshot(narrow)
        self.assertIn("512", str(caught.exception))
        # Retaining the pattern is how a mixed-snapshot import is declared.
        evidence.check_snapshot(narrow, retained=("cg_step",))

    def test_complete_side_set_is_accepted(self):
        evidence.check_snapshot([{"benchmark": "cg_step", "n": side} for side in evidence.SIDES])

    def test_mislabeled_pattern_is_rejected(self):
        with self.assertRaises(SystemExit) as caught:
            evidence.check_snapshot([{"benchmark": "step", "n": 512}])
        self.assertIn("step", str(caught.exception))

    def test_renamed_export_is_resolved_by_alternate_name(self):
        import tempfile
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            (root / "all-reducepoints.json").write_text("{}")
            self.assertEqual(evidence.resolve(root, "points.json", "all-reducepoints.json").name,
                             "all-reducepoints.json")
            with self.assertRaises(FileNotFoundError):
                evidence.resolve(root, "points.json")

    def test_incomplete_halo_matrix_is_rejected(self):
        with self.assertRaises(ValueError):
            evidence.parse_comm_matrix("2 2 2\n1 2 3\n", 2)


if __name__ == "__main__":
    unittest.main()
