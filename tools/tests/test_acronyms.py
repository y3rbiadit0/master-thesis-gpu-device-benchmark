"""Acronyms are expanded at their first prose use in each scope, and only there."""

import importlib.util
import unittest
from pathlib import Path

spec = importlib.util.spec_from_file_location("check_thesis", Path(__file__).parents[1] / "check_thesis.py")
checker = importlib.util.module_from_spec(spec)
spec.loader.exec_module(checker)

DEFINITIONS = checker.acronym_definitions(r"""
\acro{GPU}{Graphics Processing Unit}
\acro{MPI}{Message Passing Interface}
\acro{DPCPP}[DPC++]{Data Parallel C++}
""")


def errors(*scopes):
    return checker.acronym_errors([[("t", text) for text in scope] for scope in scopes], DEFINITIONS)


class AcronymTests(unittest.TestCase):
    def test_definition_then_plain_use_passes(self):
        self.assertEqual(errors([r"\acp{GPU} run \ac{MPI} and \ac{DPCPP}; later GPUs, MPI, DPC++."]), [])

    def test_plain_use_before_definition_is_rejected(self):
        self.assertIn("t: GPU used before its \\ac definition",
                      errors([r"A GPU. \ac{GPU} \ac{MPI} \ac{DPCPP}"]))

    def test_second_definition_is_rejected(self):
        self.assertIn("t: MPI defined again; use plain text after the first \\ac",
                      errors([r"\ac{GPU} \ac{MPI} \ac{DPCPP} \ac{MPI}"]))

    def test_reset_scope_requires_a_new_definition(self):
        found = errors([r"\ac{GPU} \ac{MPI} \ac{DPCPP}"], ["The GPU."])
        self.assertIn("t: GPU used before its \\ac definition", found)

    def test_hand_written_expansion_is_rejected(self):
        found = errors([r"\ac{GPU} \ac{MPI} \ac{DPCPP}, Message Passing Interface (MPI)"])
        self.assertIn("t: hand-written expansion (MPI); use \\ac{MPI}", found)

    def test_unlisted_acronym_is_rejected_but_names_and_code_are_not(self):
        found = errors([r"\ac{GPU} \ac{MPI} \ac{DPCPP} over RDMA, NVLink, \texttt{UCX\_TLS}, HPC-X."])
        self.assertEqual(found, ["t: unlisted acronym RDMA"])

    def test_headings_do_not_count_as_first_use(self):
        found = errors([r"\subsubsection{MPI Paths} \ac{MPI} \ac{GPU} \ac{DPCPP}"])
        self.assertEqual(found, [])

    def test_table_of_contents_heading_must_spell_acronyms_out(self):
        found = errors([r"\section{MPI Paths} \subsubsection{MPI Detail} \ac{MPI} \ac{GPU} \ac{DPCPP}"])
        self.assertEqual(found, ["t: acronym MPI in table-of-contents heading; spell it out"])

    def test_unused_definition_is_rejected(self):
        self.assertIn(f"{checker.ACRONYM_LIST}.tex: DPCPP is never used",
                      errors([r"\ac{GPU} \ac{MPI}"]))


if __name__ == "__main__":
    unittest.main()
