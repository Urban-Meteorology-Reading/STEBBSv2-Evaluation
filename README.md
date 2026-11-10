# STEBBSv2-Evaluation

Python scripts, Jupyter notebooks, and supporting data for site parameter
derivation, model evaluation, and visualisation for the research paper:

**Building energy modelling for urban weather and climate studies: STEBBS v2.0**

*Yiqing Liu, Denise Hertwig, Keisuke Nakao, Stefán T. Smith, Andreas Christen, Robin J. Hogan, Vitor Lavor, Matthew Paskin, James Matthews, Silvia Rognone, Leon Sander, Markus Sulzer, Ting Sun, Sue Grimmond*

Prepared for submission to **Geoscientific Model Development**.

The site characterisation focuses on the 250 m × 250 m neighbourhood around
the BRTYND ASSURE-urbisphere site in Tyndall's Park, Bristol. The evaluation
notebooks compare SUEWS-STEBBS and EnergyPlus simulations with indoor
observations, and assess solar radiation splitting methods at sites in
Bristol and Berlin.

## Repository structure

```text
STEBBSv2-Evaluation/
├── BRTYND_site_characterisation/
│   ├── BRTYND_buildings_prepare.py   # Prepare building geometry and attributes
│   ├── BRTYND_landcover.py           # Derive SUEWS land-cover fractions
│   ├── BRTYND_building_profiles.py   # Building area, perimeter and diameter by height
│   ├── BRTYND_building_fai.py        # Frontal area index for 16 wind directions
│   ├── BRTYND_building_roughness.py  # Roughness, displacement height and height statistics
│   └── output/                      # Derived site parameters in CSV format
├── input/
│   └── BRTYND_grid/                 # Site grid and buffered grid shapefiles (EPSG:27700)
├── Evaluation/
│   ├── stebbs_evaluation.ipynb         # Indoor temperatures and building energy analyses
│   ├── solar_radiation_evaluation.ipynb # Perez/Reindl radiation splitting and ERA5 comparisons
│   ├── ERA5_radiation/                 # Bristol hourly ERA5 radiation data
│   ├── sample_indoor_observation/      # Processed indoor temperature sample
│   ├── colourmaps/                     # Colourmap tables, documentation and licence
│   └── figures/                       # Saved paper figures
└── README.md
```

## Data availability

The modelling inputs and outputs for both SUEWS-STEBBS and EnergyPlus are
archived on Zenodo: [10.5281/zenodo.23955440](https://doi.org/10.5281/zenodo.23955440).

Outdoor meteorological and radiation observations are embargoed and are
not currently publicly available. They are not included in this repository or the
Zenodo modelling archive. The processed indoor
evaluation sample and ERA5 radiation data are included in this repository.

## Using the repository

**Site characterisation.** Run scripts from `BRTYND_site_characterisation/`
so their relative paths resolve correctly. Create `output/temp/` first.
Run `BRTYND_buildings_prepare.py` before the profile and frontal-area scripts;
run `BRTYND_building_roughness.py` after building preparation, land cover, and
frontal area calculations. These scripts use NumPy, pandas, GeoPandas, and
Shapely; building preparation also requires QGIS and its Python processing
tools. The raw Ordnance Survey building-height and topography datasets must
be supplied separately under `input/OSBuildingHeights/` and
`input/OSTopography/`, with paths adjusted in the scripts. These inputs and
temporary processing files are excluded from version control; derived CSVs
are included in `output/`.

**Model evaluation.** Open
[`stebbs_evaluation.ipynb`](Evaluation/stebbs_evaluation.ipynb) with
`Evaluation/` as the working directory. Set `MODEL_DATA` to the extracted
modelling-data folder containing `SUEWS_STEBBS_modelling/` and
`EnergyPlus_modelling/` from the Zenodo archive above, then
run cells in order to generate Figures 10–15. The required `vik.txt` and
`vik_neutral.txt` colourmap tables are included in `Evaluation/colourmaps/`;
see the [colourmap documentation](Evaluation/colourmaps/README.md). This analysis uses existing model outputs;
no simulation rerun is needed. The
[included indoor sample](Evaluation/sample_indoor_observation/) covers
July and 26 November–16 December 2025 at 15-minute resolution.

**Solar radiation evaluation.**
[`solar_radiation_evaluation.ipynb`](Evaluation/solar_radiation_evaluation.ipynb)
contains the analysis code for Figure 8 and Figures S6.1–S6.2. Running it
requires authorised access to the embargoed outdoor meteorological and
radiation observations. Both notebooks use
NumPy, pandas, Matplotlib, and Jupyter; the solar radiation notebook also
uses pvlib. Figures are saved to
`Evaluation/figures/`.
