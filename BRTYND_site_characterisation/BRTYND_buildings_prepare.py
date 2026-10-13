"""
Process OS MasterMap Building Height Attribute data for the
Tyndall's Park Bristol neighbourhood around the ASSURE-urbisphere
site BRTYND to prepare the data for further processing

Raw OS data obtained from:
OS MasterMap Building Height Attribute [FileGeoDatabase geospatial data], Scale 1:2500, Tiles: st57se,st67sw, Updated: 9 March 2023, Ordnance Survey (GB), Using: EDINA Digimap Ordnance Survey Service, <https://digimap.edina.ac.uk>, Downloaded: 2023-12-13 15:57:52.199

The processing follows the MAPSECC methodology described in:
Hertwig et al. (2025). Connecting Physical and Socio-Economic Spaces for Multi-Scale Urban Modelling: A Dataset for London. Geoscience Data Journal, 12, e289, https://doi.org/10.1002/gdj3.289

Using
- Python v3.12.13
- GeoPandas v1.1.4
- Pandas v3.0.3
- Numpy v2.5.1
- QGIS v3.44

D Hertwig
"""
from qgis.core import *
import processing
from processing.core.Processing import Processing
from qgis.analysis import QgsNativeAlgorithms
from qgis.PyQt.QtCore import QVariant
import numpy as np
import os
import geopandas
import pandas as pd
pd.options.mode.chained_assignment = None  # default='warn'
from datetime import datetime

app = QgsApplication([],True)
Processing.initialize()
QgsApplication.processingRegistry().addProvider(QgsNativeAlgorithms())

# Import 250 m x 250 m BRTYND neighbourhood grid domain
BRTYND_domain = geopandas.read_file('../input/BRTYND_grid/BRTYND_grid_27700_buffered.shp')
cols_to_keep = ['layer','geometry']
BRTYND_domain = BRTYND_domain[cols_to_keep].copy(deep=True)
BRTYND_domain['grid_250m'] = np.nan
BRTYND_domain['grid_250m'] = BRTYND_domain['grid_250m'].astype('object')
BRTYND_domain.loc[BRTYND_domain['layer']=='SphereHouse_grid_27700','grid_250m'] = 'grid_250m'
BRTYND_domain.loc[BRTYND_domain['layer']=='Symmetrical difference','grid_250m'] = 'outside'
BRTYND_domain.to_file('./output/temp/BRTYND_domain_buffered.shp')

path_temp = './output/temp/'
sr = 'BRTYND'
#______________________________________________________
# BUILDING ANALYSIS - including buffer
#______________________________________________________
fout = './output/temp/gdf_bldgs_in_BRTYND_grid_buffered.shp'
vl1 = QgsVectorLayer('../input/OSBuildingHeights/Download_2409900/mastermap_building_heights_5324118/st/st5570.gdb', 'polygon', 'ogr')
vl2 = QgsVectorLayer('./output/temp/BRTYND_domain_buffered.shp', 'polygon', 'ogr')
p = processing.run("native:joinattributesbylocation", {
            'INPUT':vl1, 
            'JOIN':vl2,
            'PREDICATE':[0,5], # intersects & within
            'JOIN_FIELDS':['grid_250m'],
            'METHOD':2, # Take attributes of the feature with largest overlap only (one-to-one)
            'DISCARD_NONMATCHING':False,
            'PREFIX':'',
            'OUTPUT':fout})
#________________________________________
# Prepare data
keep = ['grid_250m', 'outside']
gdf_bldgs = geopandas.read_file(fout)
gdf_bldgs = gdf_bldgs.loc[gdf_bldgs['grid_250m'].isin(keep)]
gdf_bldgs.to_file(fout)

#_____________________________________________________
# (2) Compute some building geometry features
#__________________________________________________________
# (2.1) Building footprint area
#__________________________________________________________
print("\n___ Computing feature geometries ___")
gdf_bldgs = geopandas.read_file(fout)
gdf_bldgs["bldgarea"]  = gdf_bldgs.area
gdf_bldgs.to_file(fout)

#__________________________________________________________
# (2.2) External wall lengths + area
#__________________________________________________________
print("\n___ Computing length and area of external walls ___")
vl_bldg = QgsVectorLayer(fout, 'polygon', 'ogr')

#~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
# 2.2.1 Get outer boundaries of buildings
#~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
# (i) Dissolve geometry
fout_dissolved_temp = "%s_dissolved.shp" %sr
if os.path.isfile(path_temp + fout_dissolved_temp):
    print("Dissolved building features already exist!")
else:
    print("Dissolving geometry...")
    processing.run("native:dissolve", {
                'INPUT':vl_bldg, 
                'OUTPUT':path_temp + fout_dissolved_temp})

# (ii) Multiparts to single parts (regroup geometry)
vl_diss = QgsVectorLayer(path_temp + fout_dissolved_temp, 'polygon', 'ogr')
fout_dissolved_single_parts_temp = "%s_dissolved_single.shp" %sr
if os.path.isfile(path_temp + fout_dissolved_single_parts_temp):
    print("Single parts already exist!")
else:
    print("Creating single parts from multiparts...")
    processing.run("native:multiparttosingleparts", {
                'INPUT':vl_diss,
                'OUTPUT':path_temp + fout_dissolved_single_parts_temp})
    # --> use this later for the oriented bounding boxes!!!

# (iii) Polygon to Lines (Outlines of building blocks)
vl_diss_outline = QgsVectorLayer(path_temp + fout_dissolved_single_parts_temp, 'polygon', 'ogr')
fout_diss_outline_temp = "%s_dissolved_outline.shp" %sr
if os.path.isfile(path_temp + fout_diss_outline_temp):
    print("Outlines of buildings already exist!")
else:
    print("Creating outlines of buildings (outer walls)...")
    processing.run("native:polygonstolines", {
                'INPUT':vl_diss_outline,
                'OUTPUT':path_temp + fout_diss_outline_temp})

#~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
# 2.2.2 Get individual (small-part) line segments of building polygons
#~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
fout_segments_temp = "%s_line_segments.shp" %sr
if os.path.isfile(path_temp + fout_segments_temp):
    print("Wall segements of buildings already exist!")
else:
    print("Creating wall segments of buildings...")
    processing.run("native:polygonstolines", {
                'INPUT':vl_bldg,
                'OUTPUT':path_temp + fout_segments_temp})

#~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
# 2.2.3 Get intersection between boundaries and derive lengths and areas
#~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
vl_outer = QgsVectorLayer(path_temp + fout_diss_outline_temp, 'polygon', 'ogr')
vl_all   = QgsVectorLayer(path_temp + fout_segments_temp, 'polygon', 'ogr')
fout_exwall_temp = "%s_external_walls.shp" %sr
if os.path.isfile(path_temp + fout_exwall_temp):
    print("External walls already exist!")
else:
    print("Isolating external walls...")
    processing.run("native:intersection", {
                'INPUT':vl_all,
                'OVERLAY':vl_outer,
                'INPUT_FIELDS':[],
                'OVERLAY_FIELDS':['os_topo_to'],
                'OVERLAY_FIELDS_PREFIX':'',
                'OUTPUT':path_temp + fout_exwall_temp})

#~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
# 2.2.4 Compute external wall parameters
#~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
fout_walls = "%s_2-2.shp"%sr
if os.path.isfile(path_temp + fout_walls):
    print("Building file with external wall attributes already exists!")
else:
    print("Creating building file with external wall attributes...")
    gdf = geopandas.read_file(path_temp + fout_exwall_temp)
    gdf["exwalllen"]  = gdf.length
    gdf["exwallarh2"] = gdf["exwalllen"] * gdf["relh2"]
    gdf["exwallarhx"] = gdf["exwalllen"] * gdf["relhmax"]

    #____________________________
    # Join information from line layer back with building polygon layer
    # Internal polygons that have no external walls will be counted as non-matching 
    # these have NaN values for the exwall attributes
    gdf_buildings = geopandas.read_file(fout)
    gdf_buildings = gdf_buildings.merge(gdf[['os_topo_to','exwalllen','exwallarh2','exwallarhx']], how = 'left', on='os_topo_to')

    # Set NULL values to 0 (=> buildings without external walls)
    cols = ['exwalllen', 'exwallarh2', 'exwallarhx']
    gdf_buildings[cols] = gdf_buildings[cols].fillna(0)
    # Save to file
    gdf_buildings.to_file(path_temp + fout_walls)

    # Check for houses that are cut!
    d_num = len(gdf_buildings['os_topo_to'])-len(gdf_buildings['os_topo_to'].drop_duplicates())
    if d_num > 0:
        print("Duplicates after wall length: %d"%d_num)
        pdb.set_trace()
        gdf_dupl = gdf[gdf.duplicated(['os_topo_to'], keep=False)]
        gdf_dupl.to_file(path_temp + "dupl.shp")

#__________________________________________________________
# (2.3) Aspect ratio and building length/depth
#__________________________________________________________
print("\n___ Computing building aspect ratio features ___")

# (i) Create bbox for individual building features
vl_bldg = QgsVectorLayer(path_temp + fout_walls, 'polygon', 'ogr')
fout_dbboxbldgs_temp = "%s_bbox_bldgs.shp" %sr

if os.path.isfile(path_temp + fout_dbboxbldgs_temp):
    print("Oriented bounding boxes for building features already exist!")
else:
    print("Creating oriented bounding boxes for building features...")
    processing.run("native:orientedminimumboundingbox", {
            'INPUT':vl_bldg,
            'OUTPUT':path_temp + fout_dbboxbldgs_temp})

# (ii) Join side length attributes to building polygons
fout_ratio = "%s_2-3.shp"%sr
if os.path.isfile(path_temp + fout_ratio):
    print("Building file with side lengths already exists!")
else:
    print("Creating building file with side lengths...")
    gdf_buildings = geopandas.read_file(path_temp + fout_walls)
    gdf_box = geopandas.read_file(path_temp + fout_dbboxbldgs_temp)
    gdf_buildings = gdf_buildings.merge(gdf_box[['os_topo_to','width','height']], how = 'left', on='os_topo_to')
    gdf_buildings = gdf_buildings.rename(columns={'width':'bbox_side1'})
    gdf_buildings = gdf_buildings.rename(columns={'height':'bbox_side2'})
    gdf_buildings.to_file(path_temp + fout_ratio)


#_________________________________________________________________________________________
# (3) Identify main and minor structures
#__________________________________________________________
# Lots of small-scale features in the OS building file are not standalone
# buildings (parent buildings), but are smaller elements that may belong to a
# parent structure (e.g., balconies, annexes, etc.) or are standalone (e.g., sheds, garages)
print("\n___ Identifying parent and daughter buildings ___")

fout_main_bldgs = "%s_3-0.shp"%sr
if os.path.isfile(path_temp + fout_main_bldgs):
    print("Building file with parent IDs already exists!")
else:
    print("Creating building file parent IDs...")
    gdf_all = geopandas.read_file(path_temp + fout_ratio)
    gdf_line_segments = geopandas.read_file(path_temp + fout_segments_temp)

    # Area ratio: to measure how elongated a structure is (deviation from circle) 
    gdf_line_segments['circum'] = gdf_line_segments.length
    gdf_line_segments['A_ratio'] = gdf_line_segments['bldgarea'] / (gdf_line_segments['circum']**2 / (4*np.pi)) 
    gdf_all = gdf_all.merge(gdf_line_segments[['os_topo_to','A_ratio','circum']], how = 'left', on='os_topo_to')
    # Length ratio: to measure how attached a structure is
    # gdf_all['L_ratio'] = gdf_all['exwalllen'] / gdf_all['circum']

    print("Extract daughters...")
    # Extract daughter buildings
    fout_daughters = "%s_1_daughters_1.shp"%sr
    mask = (gdf_all['A_ratio']<=0.075) |\
            ((gdf_all['A_ratio']<=0.15) & (gdf_all["bldgarea"]/(gdf_all["bbox_side1"]*gdf_all["bbox_side2"]) <= 0.33)) |\
            (gdf_all["bldgarea"] <= 30.0) | (gdf_all["bbox_side1"] <= 3.0) |\
            (gdf_all["bbox_side2"] <= 3.0) |\
            (gdf_all["bldgarea"]/(gdf_all["bbox_side1"]*gdf_all["bbox_side2"]) <= 0.33) |\
            (((gdf_all["relh2"] < 2.7) | (gdf_all["relh2"].isna())) & ((gdf_all["relhmax"] < 2.7) | (gdf_all["relhmax"].isna())))
    gdf_daughters = (gdf_all.loc[mask]).copy(deep=True)       
    gdf_daughters["parent"] = 'false'

    # Further checks (e.g., isolated daughters, very large daughters, daughters only having daughters as neighbours)
    gdf_daughters_checks = (gdf_daughters.loc[(gdf_daughters['A_ratio']>0.05) & (gdf_daughters['bldgarea']>= 80.0) & ~((((gdf_daughters["relh2"] < 2.7) | (gdf_daughters["relh2"].isna())) & ((gdf_daughters["relhmax"] < 2.7) | (gdf_daughters["relhmax"].isna()))))]).copy(deep=True)
    # gdf_daughters_checks.to_file(path_temp + 'gdf_daughters_checks.shp')
    gdf_all['parent'] = 'true'
    gdf_all.loc[gdf_all["os_topo_to"].isin(gdf_daughters["os_topo_to"]),'parent'] = 'false'        
    
    for idx, row in gdf_daughters_checks.iterrows():
        all_touching = gdf_all.loc[gdf_all.geometry.touches(row.geometry)]            
        if len(all_touching.index) > 0:  # is not isolated
            if (all_touching['parent'].nunique() == 1) & (all_touching['parent'].unique()[0] == 'false'):  # all touching are daughter buildings
                gdf_daughters_checks.loc[idx, 'parent'] = 'true' # switch back to parent
            else:
                all_touching_parent = all_touching.loc[all_touching['parent']=='true']
                parent_area_max = all_touching_parent['bldgarea'].max()
                if parent_area_max < 1.0 * row['bldgarea']:
                    gdf_daughters_checks.loc[idx, 'parent'] = 'true' # switch back to parent
        else:
            gdf_daughters_checks.loc[idx, 'parent'] = 'true' # switch back to parent     

    cleanup = gdf_daughters_checks.loc[gdf_daughters_checks['parent']=='true']['os_topo_to'].tolist()
    gdf_daughters = gdf_daughters.loc[~gdf_daughters['os_topo_to'].isin(cleanup)]
    gdf_daughters.to_file(path_temp + fout_daughters)

    #_____________________________________
    # Extract parent buildings
    print("Extract parents...")
    fout_parents = "%s_1_parents_1.shp"%sr
    gdf_all = geopandas.read_file(path_temp + fout_ratio)
    gdf_parents = (gdf_all.loc[~gdf_all["os_topo_to"].isin(gdf_daughters["os_topo_to"])]).copy(deep=True)
    gdf_parents["parent"] = 'true'
    gdf_parents["parentID"] = gdf_parents["os_topo_to"]
    gdf_parents.to_file(path_temp + fout_parents)

    #_____________________________________
    print("Mapping parentID to daughter: (1) direct neighbours")
    # IDs to daughters (daughters sharing a border with a parent)
    fout_daughter_ID_1 = "%s_1_ID_1.shp"%sr        
    vl1 = QgsVectorLayer(path_temp + fout_daughters, 'polygon', 'ogr')
    vl2 = QgsVectorLayer(path_temp + fout_parents, 'polygon', 'ogr')
    processing.run("native:joinattributesbylocation", {
                'INPUT':vl1,
                'JOIN':vl2,
                'PREDICATE':[3], # touches
                'JOIN_FIELDS':['parentID'],
                'METHOD':2, # largest touching area
                'DISCARD_NONMATCHING':False,
                'PREFIX':'',
                'OUTPUT':path_temp + fout_daughter_ID_1})

    # print("Mapping parentID to daughter: direct neighbours")
    # geopandas equivalent - takes longer
    # fout_daughter_ID_1_test = "%s_1_ID_1__test.shp"%sr
    # for idx, row in gdf_daughters.iterrows():
    #     all_touching = gdf_parents.loc[gdf_parents.geometry.touches(row.geometry)]
    #     if len(all_touching.index) > 0:
    #         idx_max = all_touching.intersection(row.geometry).length.idxmax()
    #         gdf_daughters.loc[idx, 'parentID'] = all_touching.loc[idx_max,'os_topo_to']
    # gdf_daughters.to_file(path_temp + fout_daughter_ID_1_test)
    # pdb.set_trace()

    #_____________________________________
    print("Mapping parentID to daughter: (2) one degree of separation")
    # Extract daughter & parent buildings
    # 1 degree of separation from parent building
    fout_daughters_2 = "%s_1_daughters_2.shp"%sr
    fout_parents_2 = "%s_1_parents_2.shp"%sr

    gdf_ID_1 = geopandas.read_file(path_temp + fout_daughter_ID_1)
    gdf_daughters_2 = (gdf_ID_1.loc[gdf_ID_1["parentID"].isna()]).copy(deep=True)
    gdf_parents_2   = (gdf_ID_1.loc[~gdf_ID_1["parentID"].isna()]).copy(deep=True)
    gdf_daughters_2.to_file(path_temp + fout_daughters_2)
    gdf_parents_2.to_file(path_temp + fout_parents_2)
    
    # ADD SPLIT 2 IDs to daughters
    fout_daughter_ID_2 = "%s_1_ID_2.shp"%sr
    vl5 = QgsVectorLayer(path_temp + fout_daughters_2, 'polygon', 'ogr')
    vl6 = QgsVectorLayer(path_temp + fout_parents_2, 'polygon', 'ogr')
    processing.run("native:joinattributesbylocation", {
                'INPUT':vl5,
                'JOIN':vl6,
                'PREDICATE':[3], # touches
                'JOIN_FIELDS':['parentID'],
                'METHOD':2,
                'DISCARD_NONMATCHING':False,
                'PREFIX':'',
                'OUTPUT':path_temp + fout_daughter_ID_2})

    #_____________________________________
    print("Mapping parentID to daughter: (3) two degrees of separation")
    # Extract daughter & parent buildings
    # 2 degrees of separation from parent building
    fout_daughters_3 = "%s_1_daughters_3.shp"%sr
    fout_parents_3 = "%s_1_parents_3.shp"%sr

    gdf_ID_2 = geopandas.read_file(path_temp + fout_daughter_ID_2)
    gdf_daughters_3 = (gdf_ID_2.loc[gdf_ID_2["parentID_2"].isna()]).copy(deep=True)
    gdf_parents_3   = (gdf_ID_2.loc[~gdf_ID_2["parentID_2"].isna()]).copy(deep=True)
    gdf_daughters_3.to_file(path_temp + fout_daughters_3)
    gdf_parents_3.to_file(path_temp + fout_parents_3)

    # ADD SPLIT 3 IDs to daughters
    fout_daughter_ID_3 = "%s_1_ID_3.shp"%sr
    vl8 = QgsVectorLayer(path_temp + fout_daughters_3, 'polygon', 'ogr')
    vl9 = QgsVectorLayer(path_temp + fout_parents_3, 'polygon', 'ogr')
    processing.run("native:joinattributesbylocation", {
                'INPUT':vl8,
                'JOIN':vl9,
                'PREDICATE':[3], # touches
                'JOIN_FIELDS':['parentID_2'],
                'METHOD':2,
                'DISCARD_NONMATCHING':False,
                'PREFIX':'',
                'OUTPUT':path_temp + fout_daughter_ID_3})

    #_____________________________________
    print("Combine data...")
    gdf_buildings = geopandas.read_file(path_temp + fout_ratio)
    vl_parents = geopandas.read_file(path_temp + fout_parents)
    vl_daugh_1 = geopandas.read_file(path_temp + fout_daughter_ID_1)
    vl_daugh_2 = geopandas.read_file(path_temp + fout_daughter_ID_2)
    vl_daugh_3 = geopandas.read_file(path_temp + fout_daughter_ID_3)

    # Add parents
    gdf_comb = geopandas.sjoin(gdf_buildings, vl_parents[['geometry','parent','parentID']], how="left", predicate='contains')
    gdf_comb_a = (gdf_comb.drop(columns='index_right')).copy(deep=True)
    # Add daughters 1
    gdf_comb_1 = geopandas.sjoin(gdf_comb_a, vl_daugh_1[['geometry','parent','parentID']], how="left", predicate='contains')
    gdf_comb_b = (gdf_comb_1.drop(columns='index_right')).copy(deep=True)
    gdf_comb_b = gdf_comb_b.rename(columns={'parent_left':'parent'})
    gdf_comb_b = gdf_comb_b.rename(columns={'parentID_left':'parentID'})
    gdf_comb_b = gdf_comb_b.rename(columns={'parent_right':'parent_1'})
    gdf_comb_b = gdf_comb_b.rename(columns={'parentID_right':'parentID_1'})
    # Add daughters 2
    gdf_comb_2 = geopandas.sjoin(gdf_comb_b, vl_daugh_2[['geometry','parentID_2']], how="left", predicate='contains')
    gdf_comb_c = (gdf_comb_2.drop(columns='index_right')).copy(deep=True)
    # Add daughters 3
    gdf_comb_3 = geopandas.sjoin(gdf_comb_c, vl_daugh_3[['geometry','parentID_1']], how="left", predicate='contains')
    gdf_comb_d = (gdf_comb_3.drop(columns='index_right')).copy(deep=True)
    gdf_comb_d = gdf_comb_d.rename(columns={'parentID_1_left':'parentID_1'})
    gdf_comb_d = gdf_comb_d.rename(columns={'parentID_1_right':'parentID_3'})

    # Cleaning up
    cols = [
        'parent',
        'parentID',
        'parentID_1',
        'parentID_2',
        'parentID_3'
    ]
    gdf_comb_d[cols] = gdf_comb_d[cols].fillna('false')
    
    for idx, row in gdf_comb_d.iterrows():
        if (row["parent"] == 'false'):
            if (row["parent_1"] != 'false'):
                gdf_comb_d.at[idx,"parent"] = gdf_comb_d.at[idx,"parent_1"]

    for idx, row in gdf_comb_d.iterrows():
        if (row["parentID"] == 'false'):
            if (row["parentID_1"] != 'false'):
                gdf_comb_d.at[idx,"parentID"] = gdf_comb_d.at[idx,"parentID_1"]
            elif (row["parentID_2"] != 'false'):
                gdf_comb_d.at[idx,"parentID"] = gdf_comb_d.at[idx,"parentID_2"]
            elif (row["parentID_3"] != 'false'):
                gdf_comb_d.at[idx,"parentID"] = gdf_comb_d.at[idx,"parentID_3"]

    gdf_comb_d1 = (gdf_comb_d.drop(columns=['parent_1','parentID_1','parentID_2','parentID_3'])).copy(deep=True)
    gdf_comb_d1.loc[gdf_comb_d1['parentID'] == 'false','parentID'] = np.nan
    gdf_comb_d1.to_file(fout)


#______________________________________________________
# BUILDING ANALYSIS - only within grid
#______________________________________________________
fout1 = './output/temp/gdf_bldgs_in_BRTYND_grid.shp'
keep = ['grid_250m']
gdf_bldgs = geopandas.read_file(fout)
gdf_bldgs = gdf_bldgs.loc[gdf_bldgs['grid_250m'].isin(keep)]
gdf_bldgs.to_file(fout1)
