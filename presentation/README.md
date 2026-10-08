# Thesis defense

- [`../thesis_defense.pptx`](../thesis_defense.pptx): editable presentation derived from `thesis_style.pptx`.
- `thesis_defense.pdf`: rendered slide preview, including the technical appendix.
- `speaker_notes.md`: generated rehearsal script, timing, and slide-level sources. The same notes are embedded in PowerPoint.
- `source_manifest.json`: generated data hashes and the exact numeric series in each editable chart.

## Presenting

The English main talk is slides **1–14**, designed for a mixed committee. Speaker-note targets total **14 minutes**, leaving a one-minute buffer in a 15-minute slot. Finish on the Questions slide. Slides **15–20** are technical backup material for questions; they are deliberately accessible after the main conclusion.

The solver charts use the thesis's **fastest residual-valid trial** convention; the first backup slide also shows medians. Primitive and MoE centers follow the retained campaign's aggregation policy. Neither small point-estimate differences nor the exploratory NCCL study establish an initiation-only speedup.

## Rebuilding

Use Python with `python-pptx` and `Pillow` installed:

```sh
python3 -B tools/build_defense.py
```

The builder reads the original template and thesis evidence and writes `thesis_defense.pptx`, `speaker_notes.md`, and `source_manifest.json`. It does not modify the template or regenerate benchmark measurements. Charts and diagrams are editable PowerPoint objects. The template's original Thanks-slide attribution is retained.

After a rebuild, validate the package against `thesis_style.pptx`, render with an office application, and inspect the slides for layout and font substitution. Use the generated notes and data manifest to check timing and numerical provenance.
