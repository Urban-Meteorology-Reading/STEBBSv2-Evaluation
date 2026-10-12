"""
Process OS MasterMap Topography land use data to derive SUEWS
landcover fractions for the Tyndall's Park Bristol neighbourhood
around the ASSURE-urbisphere site BRTYND

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
from datetime import datetime

# current time
release_date = datetime.today().strftime('%Y-%m-%d %H:%m')

# Import 250 m x 250 m BRTYND neighbourhood grid domain
BRTYND_domain = geopandas.read_file('../input/BRTYND_grid/BRTYND_grid_27700.shp')
BRTYND_domain['grid_250m'] = 'grid_250m'
BRTYND_domain.to_file('./output/temp/BRTYND_domain.shp')

# OS MasterMap Topography land use data
path_lc = "../input/OSTopography/Download_2409903/mastermap-topo_5324121/"
file_lc = 'mastermap-topo_5324121.gdb'
# Load land cover (masked)
gdf_lc = geopandas.read_file(path_lc + file_lc, layer='Topgraphicarea', mask = BRTYND_domain) 
# gdf_lc.to_file('./output/temp/gdf_lc.shp')

#___________________________
grid_nums = BRTYND_domain['grid_250m'].unique().tolist() # just a single grid
n_grid_nums = len(grid_nums)
grid_lc = np.zeros((len(grid_nums),23))
# loop through all grids in domain
for count, grid in enumerate(grid_nums):
    # clip polygons in working grid
    work_grid = BRTYND_domain.loc[BRTYND_domain['grid_250m'] == grid]
    work_grid_area = work_grid.area.values[0]
    work_lc = geopandas.clip(gdf_lc, work_grid)
    # work_lc.to_file('./output/temp/work_lc.shp')
    
    #____________________________________
    # Landuse combinations in BRTYND grid:
    #____________________________________
    # work_lc['descriptivegroup'].unique().tolist()
    #    --> ['General Surface', 'Building', 'Road Or Track', 'Roadside', 'Path', 'Path,Structure']
    # work_lc.loc[work_lc['descriptivegroup']=='Path,Structure']['descriptiveterm'].unique().tolist()
    #    --> ['Step', 'Footbridge']
    # work_lc.loc[work_lc['descriptivegroup']=='General Surface']['make'].unique().tolist()
    #    --> ['Multiple', 'Manmade', 'Natural']
    #____________________________________
    # (1) Buildings
    lc_bldg  = (work_lc.loc[work_lc['descriptivegroup'] == 'Building'].copy(deep=True)).dissolve()
    lc_bldg_area  = lc_bldg.area.values[0] if len(lc_bldg) > 0 else 0

    # (2) Paved (roads, pavement, paths)
    paved_types = ['Road Or Track', 'Roadside', 'Path', 'Path,Structure']
    lc_paved_roads = (work_lc.loc[(work_lc['descriptivegroup'].isin(paved_types))].copy(deep=True)).dissolve()
    lc_paved_roads_area = lc_paved_roads.area.values[0] if len(lc_paved_roads) > 0 else 0

    # (3) 'General Surface' -  combines different surface types
    lc_general_surface  = work_lc.loc[work_lc['descriptivegroup'] == 'General Surface'].copy(deep=True)
    
    # i. vegetation
    lc_gs_veg   = (lc_general_surface.loc[lc_general_surface['make']=='Natural'].copy(deep=True)).dissolve()
    lc_gs_veg_area = lc_gs_veg.area.values[0] if len(lc_gs_veg) > 0 else 0

    # ii. paved
    lc_gs_paved = (lc_general_surface.loc[lc_general_surface['make']=='Manmade'].copy(deep=True)).dissolve()
    lc_gs_paved_area = lc_gs_paved.area.values[0] if len(lc_gs_paved) > 0 else 0

    # iii. mixed
    lc_gs_multi      = (lc_general_surface.loc[lc_general_surface['make']=='Multiple'].copy(deep=True)).dissolve()
    lc_gs_multi_area = lc_gs_multi.area.values[0] if len(lc_gs_multi) > 0 else 0
    
    # Split vegetated and paved
    veg_frac_of_multi = 0.5  # Veg-Paved split assumed for multi surfaces
    # Total paved surface
    lc_paved_area = lc_paved_roads_area + lc_gs_paved_area + (1.0-veg_frac_of_multi)*lc_gs_multi_area
    # Total vegetated surface
    lc_veg_area = lc_gs_veg_area + veg_frac_of_multi*lc_gs_multi_area

    # Split grass and trees
    grass_frac_of_total_veg = 0.50
    lc_grass_area = grass_frac_of_total_veg * lc_veg_area
    lc_tree_area  = (1.0-grass_frac_of_total_veg) * lc_veg_area
    
    # Split trees by type
    dectr_frac_of_total_tree = 0.85
    lc_dectr_area = dectr_frac_of_total_tree * lc_tree_area
    lc_evetr_area = (1.0-dectr_frac_of_total_tree) * lc_tree_area

    total_area = lc_dectr_area + lc_evetr_area + lc_grass_area + lc_paved_area + lc_bldg_area
    # Check if consistent with total grid area
    print("Area ratio: ", total_area / work_grid_area)
    if total_area / work_grid_area > 1.1:
        print("Area ratio > 1.1 - checks needed")

    #________________________
    # Gather data
    #________________________
    # 0: grid ID
    # 1: gridbox area [m2]
    # 2: Buildings: plan area fraction [-]
    # 3: Paved/impervious surface: plan area fraction [-]
    # 4: Grass: plan area fraction [-]
    # 5: Evergreen Tree: plan area fraction [-]
    # 6: Greenleaf Tree: plan area fraction [-]
    # 7: Water: plan area fraction [-]
    # 8: Bare soil: plan area fraction [-]
    grid_lc[count,0] = 1
    grid_lc[count,1] = work_grid.geometry.area.sum()
    if total_area > 0:
        grid_lc[count,2] = lc_bldg_area  / total_area
        grid_lc[count,3] = lc_paved_area / total_area
        grid_lc[count,4] = lc_grass_area / total_area
        grid_lc[count,5] = lc_evetr_area / total_area
        grid_lc[count,6] = lc_dectr_area / total_area
        grid_lc[count,7] = 0.0 # only for BRTYND grid!
        grid_lc[count,8] = 0.0 # only for BRTYND grid!
    else:
        grid_lc[count,2] = np.nan
        grid_lc[count,3] = np.nan
        grid_lc[count,4] = np.nan
        grid_lc[count,5] = np.nan
        grid_lc[count,6] = np.nan
        grid_lc[count,7] = np.nan
        grid_lc[count,8] = np.nan

df_lc  = pd.DataFrame({'release'      : release_date,
                       'ref_year'     : '05/2023',
                        'SH_grid'     : 'grid_250m',
                        'area_grid'   : grid_lc[:,1],
                        'frac_bldgs'  : grid_lc[:,2],
                        'frac_paved'  : grid_lc[:,3],
                        'frac_grass'  : grid_lc[:,4],
                        'frac_evetr'  : grid_lc[:,5],
                        'frac_dectr'  : grid_lc[:,6],
                        'frac_water'  : grid_lc[:,7],
                        'frac_bsoil'  : grid_lc[:,8]
                        })
    
# Save output
df_lc.to_csv('./output/BRTYND_landcover.csv', index=False)