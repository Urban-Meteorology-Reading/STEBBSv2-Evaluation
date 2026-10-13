"""
Process building data for the Tyndall's Park Bristol neighbourhood 
around the ASSURE-urbisphere site BRTYND to derive height
profiles (1 m increments) of
    - building plan area fraction
    - total building perimeter length (exposed walls only)
    - normalised building perimeter length
    - effective building diameter

This uses preprocessed building polygons that are the OUTPUT of
    - BRTYND_buildings_prepare.py

The processing follows the MAPSECC methodology described in:
Hertwig et al. (2026). MAPSECC: London v2.0-new building roughness and morphology parameters.
Geoscience Data Journal, 13, e70086, https://doi.org/10.1002/gdj3.70086 

Using
- Python v3.12.13
- GeoPandas v1.1.4
- Pandas v3.0.3
- Numpy v2.5.1

D Hertwig
"""
import numpy as np
import geopandas
import pandas as pd

def compute_pai_L(work_grid, work_bldgs, work_bldgs_buffered):
    """
    (1) Compute building plan area index in a selected grid.
    (2) Compute total building perimeter length (L, m) and its normalised 
    (by the grid cell area) version, nL (m-1) in a selected grid.
    
    :work_grid:    geodataframe, 500 m grid 
    :work_bldgs:   geodataframe, buildings in current grid
    :work_bldgs_buffered:  geodataframe, buildings in buffered current grid
    :returns:      tuple[float], (PAI (-), L (m), nL (m-1))
    """
    # (1) Plan area index (PAI)
    # re-calculate clipped area
    work_bldgs['area_new'] = work_bldgs.area 
    pai = work_bldgs['area_new'].sum() / work_grid['grid_a_m2']
    pai_out = pai.values[0]

    # (2) Total building perimeter length
    # Create a LineString version of current grid
    grid_boundary = work_grid.boundary
    gdf_boundary = geopandas.GeoDataFrame(geometry=geopandas.GeoSeries(grid_boundary))
    
    # Remove accidentially created Point geometries
    work_bldgs = work_bldgs.loc[work_bldgs.geometry.type != 'Point']
    work_bldgs_buffered = work_bldgs_buffered.loc[work_bldgs_buffered.geometry.type != 'Point']
    
    # Dissolve building Polygons in grid (creates a single Multipolygon)
    # and derive the total perimeter
    work_bldgs_dissolved = work_bldgs.dissolve()
    work_bldgs_dissolved["perimeter"] = work_bldgs_dissolved['geometry'].length
    
    # Get intersection length between grid and building polygons that lie on the 
    # grid border (i.e. artifical 'internal' walls) that don't count towards the 
    # total external perimeter length and will be removed from in a next step
    intersection = gdf_boundary.clip(work_bldgs_buffered)
    
    # Determine total external building length
    if len(intersection)>0:
        # if there are buildings intersecting w/ grid border
        # the total perimeter length is corrected
        L = work_bldgs_dissolved["perimeter"].values[0] - intersection.length.values[0]
    else:
        L = work_bldgs_dissolved["perimeter"].values[0]
    
    # Normalised building perimenter length; L (m-1)
    # Stretton et al. (2022), https://doi.org/10.1016/j.uclim.2023.101560
    nL = L / work_grid['grid_a_m2'].values[0]
    
    return (pai_out, L, nL)

# Import domain
BRTYND_domain = geopandas.read_file('../input/BRTYND_grid/BRTYND_grid_27700.shp')
BRTYND_domain['grid_250m'] = 'grid_250m'
BRTYND_domain['grid_a_m2'] = BRTYND_domain.area # grid area [m^2]
BRTYND_domain['processed'] = False  # Boolean flag to filter processed grids for subregion output

# Import building polygon data in domain
# This is the output of BRTYND_buildings_prepare.py
gdf_bldgs = geopandas.read_file('./output/temp/gdf_bldgs_in_BRTYND_grid_buffered.shp')

# Initialise output dictionaries
all_grids = BRTYND_domain['grid_250m'].tolist()
max_height = np.ceil(gdf_bldgs['relh2'].max())
dz = 1.0 # 1 m height increments
heights = np.arange(0.0,max_height+dz,dz)

pai_profile = {}
for grid in all_grids:
    pai_profile[grid] = {}
    for height in heights:
        pai_profile[grid][height] = 0.0

walllen_profile = {}
for grid in all_grids:
    walllen_profile[grid] = {}
    for height in heights:
        walllen_profile[grid][height] = 0.0

nwalllen_profile = {}
for grid in all_grids:
    nwalllen_profile[grid] = {}
    for height in heights:
        nwalllen_profile[grid][height] = 0.0

for idx, row in BRTYND_domain.iterrows():
    loop_height = True
    i_height    = 0
    n_height    = len(heights)
    # Get geometry of current grid
    work_grid = BRTYND_domain.loc[BRTYND_domain['grid_250m']==row["grid_250m"]].copy()
    work_grid_buffered = work_grid.buffer(100)
    # Clip buildings
    bldgs_in_grid = gdf_bldgs.clip(work_grid)
    bldgs_in_grid_buffered = gdf_bldgs.clip(work_grid_buffered)
        
    while loop_height:
        height = heights[i_height]
        bldgs_in_grid_at_height = bldgs_in_grid.loc[bldgs_in_grid['relh2']>=height].copy(deep=True)
        if len(bldgs_in_grid_at_height)==0:
            loop_height = False
        else:                    
            bldgs_in_grid_buffered_at_height = bldgs_in_grid_buffered.loc[bldgs_in_grid_buffered['relh2']>=height].copy(deep=True)
            vars_out = compute_pai_L(work_grid, bldgs_in_grid_at_height, bldgs_in_grid_buffered_at_height)
            # Save data to dict
            pai_profile[row["grid_250m"]][height]      = vars_out[0]
            walllen_profile[row["grid_250m"]][height]  = vars_out[1]
            nwalllen_profile[row["grid_250m"]][height] = vars_out[2]
        i_height += 1
        if i_height==n_height:
            loop_height = False

# Prepare PAI output
df_pai_out = pd.DataFrame(pai_profile) 
df_pai_out['height'] = df_pai_out.index
df_pai_out = df_pai_out[df_pai_out.columns[::-1]]
print("\tSaving PAI output...")
df_pai_out.to_csv('./output/BRTYND_PAI_profile_dz1m.csv', index=False)

# Prepare wall length (L) output
df_L_out = pd.DataFrame(walllen_profile) 
df_L_out['height'] = df_L_out.index
df_L_out = df_L_out[df_L_out.columns[::-1]]
print("\tSaving L output...")
df_L_out.to_csv('./output/BRTYND_L_profile_dz1m.csv', index=False)

# Prepare normalised wall length (nL) output
df_nL_out = pd.DataFrame(nwalllen_profile) 
df_nL_out['height'] = df_nL_out.index
df_nL_out = df_nL_out[df_nL_out.columns[::-1]]
print("\tSaving nL output...")
df_nL_out.to_csv('./output/BRTYND_nL_profile_dz1m.csv', index=False)

#_________________________________________________
# Compute effective building diameter
# and export to file
# Stretton et al. (2022), https://doi.org/10.1016/j.uclim.2023.101560
# List of grids and heights
col_list = df_pai_out.columns.unique().tolist()
grid_list = [x for x in col_list if x!='height']
heights = df_pai_out['height'].tolist()
D_all   = df_pai_out.copy(deep=True)
for grid in grid_list:
    for i in range(len(heights)):
        if df_pai_out.loc[i][grid]!=0:
            D_all.loc[i, grid] = (4.0 * df_pai_out.iloc[i][grid])/df_nL_out.iloc[i][grid]
        else:
            D_all.loc[i, grid] = 0.0
D_all_out = D_all.drop('height', axis=1)
D_all_out['height'] = D_all_out.index
D_all_out = D_all_out[D_all_out.columns[::-1]]
print("\tSaving L output...")
D_all_out.to_csv('./output/BRTYND_D_profile_dz1m.csv', index=False)