---
name: bio-reporting-figure-export
description: Export and inspect publication figures at their intended size, with editable PDF and high-resolution raster output.
---

# Publication figure export

Use the existing plotting script and its units for local edits. For new figures, set final dimensions before drawing. Consult the [publication style](../bio-publication-figure-director/references/publication-style.md) for fonts and line widths. The shared [R](../bio-publication-figure-director/scripts/publication_style.R) and [Python](../bio-publication-figure-director/scripts/publication_style.py) helpers take dimensions in mm.

Preserve vector text, lines and statistical marks in the PDF and export the PNG at the requested dimensions and DPI (300 DPI by default). Verify page size, raster dimensions and effective resolution at final placement. Render the PDF and inspect the PNG, checking changed labels, clipping and relevant data marks. Keep independent panels editable when preparing a composite.

Optional export examples are available from [bioSkills](https://github.com/GPTomics/bioSkills/tree/2fe089dfa64990d79afac39b58a16f074c29e23a).
