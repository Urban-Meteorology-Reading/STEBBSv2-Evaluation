# Colourmaps

`vik.txt` is Fabio Crameri's unmodified Scientific colour maps v8 `vik` table,
distributed through cmcrameri under the included MIT licence.

- Scientific colour maps: https://www.fabiocrameri.ch/colourmaps/
- Data citation: https://doi.org/10.5281/zenodo.1243862
- Source revision: `78f02a088fa3c4fb4cb8aa92bd8e52389ab9d09a`
- Source: https://github.com/callumrollo/cmcrameri/blob/78f02a088fa3c4fb4cb8aa92bd8e52389ab9d09a/cmcrameri/cmaps/vik.txt
- SHA-256: `60c2abfbffdfd9e7567cfeea1387bfe270eb036efe7262fdd7bf713058bacae2`

`vik_neutral.txt` is the grey-centred variant used for Figure 15. It retains the
original anchors at normalised positions <=0.42 and >=0.58 and replaces the
central anchors with RGB `#E6E6E6` at 0.5. A monotone cubic (PCHIP) interpolation
in linear-light RGB produces 4,097 samples, which are converted back to sRGB.
The precomputed table avoids a SciPy dependency when running the notebook.

This modified variant is not the original `vik` and has not been independently
validated as perceptually uniform or accessible for every colour-vision deficiency.
The licence and copyright notices apply to both tables.
