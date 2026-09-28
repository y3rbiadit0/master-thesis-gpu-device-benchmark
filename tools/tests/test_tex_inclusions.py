"""Regressions for the figure-path and table-inclusion build failures."""

import importlib.util
import unittest
from pathlib import Path


def load(name):
    spec = importlib.util.spec_from_file_location(name, Path(__file__).parents[1] / f"{name}.py")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


evidence = load("rebuild_main_evidence")
checker = load("check_thesis")


class InclusionTests(unittest.TestCase):
    def test_rejects_row_input_at_alignment_boundary(self):
        source = r"""\begin{table}
\begin{tabular}{lr}
\toprule
Name & Value\\
\midrule
\input{data/rows.tex}
\bottomrule
\end{tabular}
\end{table}"""
        self.assertEqual(checker.table_row_inputs(source), ["data/rows.tex"])

    def test_complete_table_include_is_outside_alignment(self):
        source = r"\begin{table}\input{data/table.tex}\end{table}"
        self.assertEqual(checker.table_row_inputs(source), [])

    def test_generated_block_owns_the_entire_alignment(self):
        row = r"MPI & 3.358\\"
        block = evidence.render_table("lr", ["Stack", "Latency"], [row])
        self.assertIn(r"\begin{tabular}{lr}", block)
        self.assertIn(row + "\n" + r"\bottomrule", block)
        self.assertTrue(block.endswith("\\end{tabular}\n"))
        self.assertNotIn(r"\input", block)

    def test_missing_row_terminator_is_rejected(self):
        with self.assertRaises(ValueError):
            evidence.render_table("lr", ["Stack", "Latency"], ["MPI & 3.358"])

    def test_figure_references_resolve_without_graphicspath(self):
        import re
        root = Path(__file__).resolve().parents[2]
        source = (root / "chapters/05-experimental-evaluation.tex").read_text()
        figures = re.findall(r"\\includegraphics(?:\[[^\]]*\])?\{([^}]+)\}", source)
        self.assertTrue(figures)
        for figure in figures:
            with self.subTest(figure=figure):
                self.assertTrue(figure.startswith("figures/"))
                self.assertTrue((root / figure).is_file())


if __name__ == "__main__":
    unittest.main()
