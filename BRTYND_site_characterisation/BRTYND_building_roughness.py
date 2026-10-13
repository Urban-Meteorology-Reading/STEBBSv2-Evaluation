"""
Combine building characteristics for the Tyndall's Park Bristol neighbourhood 
around the ASSURE-urbisphere site BRTYND and derive further building parameters:
    - roughness length and displacement heights
    - number of buildings in neighbourhood
    - height statistics

This combines and uses OUTPUT of
    - BRTYND_buildings_prepare.py
    - BRTYND_landcover.py
    - BRTYND_building_fai.py

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
from datetime import datetime

def macdonald(data):
    """
    Apply Macdonald et al. (1998) morphometric method
    (https://doi.org/10.1016/S1352-2310(97)00403-2)
    to determine momentum roughness length (z0)
    and displacement height (zd) for buildings

    :data:  dictionary, contains FAI, PAI, Have (m)
    :returns:  dictionary, input dictionary with Macdonald z0, zd (m) added
    """
    # Macdonald et al. (1998) parameters for
    # staggered arrays
    alpha = 4.43
    beta  = 1.0
    Cd    = 1.2 # drag coefficient
    kappa = 0.4 # von Karman constant

    data['zd_Mac'] = (1+((alpha**-data['pai'])*(data['pai']-1))) * data['h_ave']
    data['z0_Mac'] = ((1-data['zd_Mac']/data['h_ave']) * np.exp(-(0.5*beta*(Cd/kappa**2)*(1-(data['zd_Mac']/data['h_ave']))*data['fai'])**-0.5)) * data['h_ave']

    return data

def kanda(data):
    """
    Apply Kanda et al. (2013) morphometric method
    (https://doi.org/10.1007/s10546-013-9818-x)
    to determine momentum roughness length (z0)
    and displacement height (zd) for buildings.
    Note: The Kanda method requires the calculation of the Macdonald et al.
    (1998) roughness length (function: macdonald())

    :data:  dictionary, contains FAI, PAI, Have (m), Hmax (m) and Hstdev (m)
    :returns:  dictionary, input dictionary with Kanda z0, zd (m) added
    """
    # First determine z0 from Macdonald et al. (1998) method
    # with staggered array params
    data_1 = macdonald(data) # Macdonald z0, zd added
    
    # Kanda et al. (2013) - Method 1 params:
    A0 = 1.29
    B0 = 0.36
    C0 = -0.17
    A1 = 0.71
    B1 = 20.21
    C1 = -0.77
    data_1['X_Kan'] = (data_1['h_std'] + data_1['h_ave']) / data_1['h_max']
    data_1['Y_Kan'] = (data_1['pai'] * data_1['h_std']) / data_1['h_ave']
    # z_d
    data_1['zd_Kan'] = np.nan
    if data_1['X_Kan']<=1.0:
        data_1['zd_Kan'] = (C0 * data_1['X_Kan']**2.0  +  ((A0 * data_1['pai']**B0) - C0)*data_1['X_Kan']) * data_1['h_max']
    else:
        data_1['zd_Kan'] = (A0 * data_1['pai']**B0) * data_1['h_max']
    # z_0
    data_1['z0_Kan'] = np.nan
    if data_1['Y_Kan']>=0.0:
        data_1['z0_Kan'] = (B1 * data_1['Y_Kan']**2.0 + C1 * data_1['Y_Kan'] + A1) * data_1['z0_Mac']
    else:
        data_1['z0_Kan'] = 0.0
    
    del data_1['X_Kan']
    del data_1['Y_Kan']

    return data_1


#_______________________________________________________
# IMPORT DATA
#_______________________________________________________
release_date = datetime.today().strftime('%Y-%m-%d %H:%m')

# Building frontal area index (FAI)
# Output of BRTYND_building_fai.py
path_fai = "./output/"
file_fai = "BRTYND_building_FAI.csv"
gdf_fai_sectors = pd.read_csv(path_fai + file_fai)

# Surface building plan area index (PAI)
# Output of BRTYND_landcover.py
path_pai = "./output/"
file_pai = "BRTYND_landcover.csv"
gdf_pai  = pd.read_csv(path_pai + file_pai)

# Buildings in neighbourhood
# Output of BRTYND_buildings_prepare.py
gdf_bldgs = geopandas.read_file('./output/temp/gdf_bldgs_in_BRTYND_grid.shp')
gdf_bldgs['area'] = gdf_bldgs.area
gdf_bldgs['h_area'] = gdf_bldgs['relh2'] * gdf_bldgs['area']

#______________________________________________________
# Building roughness parameters
#______________________________________________________
# Collect data in dictionary
morph_out = {}
morph_out['release_date'] = release_date
morph_out['ref_year']     = '03/2023'
# Building height statistics (all in metres)
morph_out['h_ave']   = gdf_bldgs['relh2'].mean() # mean height
morph_out['h_a_ave'] = gdf_bldgs['h_area'].sum() / gdf_bldgs['area'].sum() # footprint area weighted mean
morph_out['h_std']   = gdf_bldgs['relh2'].std()  # standard deviation of heights
morph_out['h_max']   = gdf_bldgs['relh2'].max()  # max height
morph_out['h_min']   = gdf_bldgs['relh2'].min()  # min height
# Indices
morph_out['fai'] = gdf_fai_sectors['fai_m_ave'].values[0]  # unweighted mean FAI over 16 wind directions
morph_out['pai'] = gdf_pai['frac_bldgs'].values[0] # building surface fraction
# Aerodynamic roughness parameters
morph_out = kanda(morph_out) # Kanda and McDonald values
# Number of main buildings in neighbourhood
N_parents = len(gdf_bldgs.loc[gdf_bldgs['parent']=='true'])
N_lone_daughters = len((gdf_bldgs.loc[gdf_bldgs['parentID'].isna()]))
morph_out['N_bldgs'] = N_parents + N_lone_daughters

print("Saving output...")
df_morph_out = pd.DataFrame(morph_out, index=[0]) 
df_morph_out.to_csv('./output/BRTYND_building_roughness.csv', index=False)