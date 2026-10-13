"""
Process building data for the Tyndall's Park Bristol neighbourhood 
around the ASSURE-urbisphere site BRTYND to derive the building
frontal area index (FAI) for 16 wind direction transects

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
import itertools
import numpy as np
import geopandas
import pandas as pd
from datetime import datetime
from shapely.geometry import LineString, MultiPoint, Point
import pdb


def extract_polygons(line, blgds):
    """
    Extract all building polygons that intersect with a 
    given transect.

    :line:     LineString object, transect through grid centre
    :blgds:    geodataframe, buildings in grid
    :returns:  tuple, ((1) geodataframe, building polygons intersecting
               with transect; (2) float, total length of transect
               that overlaps these buildings)
    """
    inters_blgds = geopandas.sjoin(line, blgds, predicate='intersects')
    inters_blgds_list = inters_blgds['os_topo_to'].unique().tolist()
    bldgs_encountered = blgds.loc[blgds['os_topo_to'].isin(inters_blgds_list)]
    # Determine how often a transects intersects with an
    # individual polygon (can be more than once)
    bldgs_encountered['n_inters'] = np.nan
    for idx, row in bldgs_encountered.iterrows():
        inters = line.clip(row['geometry'])
        # intersecting transect segments will create a MultiLineString object (explode)
        bldgs_encountered.at[idx,'n_inters'] = len(inters.explode(index_parts=True))
    if bldgs_encountered['n_inters'].isnull().any():
        print("Number of encounters not determined for polygon!")
        pdb.set_trace()
    # total length of transect that overlaps buildings
    # (information to determine H/W)
    lines_intersecting = line.clip(bldgs_encountered)
    if not lines_intersecting.empty:
        len_intersecting = lines_intersecting.length.values[0]
    else:
        len_intersecting = 0 # no intersections found

    return bldgs_encountered, len_intersecting


def compute_fai(gdf_grid, gdf_bldgs, select_grid, angle_offset):
    """
    For a given grid-cell neighbourhood, generate transects (LineString
    objects) connecting points on the grid border with the grid centroid 
    (steps i-v) and measure the length of the transects.

    :gdf_grid:      geodataframe, grid polygons of the processing domain
    :gdf_bldgs:     geodataframe, building polygons of the processing domain
    :select_grid:   int, ID of grid for which the FAI is computed in
                    this function
    :angle_offset:  float, angle (in degrees) between neighbouring
                    transects; NOTE: the code currently expects an angle
                    increment of 22.5 deg.
    :returns:  tuple, ((1) list[float], FAI values for each transect 
               considering multiple ("m") intersections with the same building;
               (2) list[float], FAI values for each transect only 
               considering single ("s") intersections with the same building)
    """

    #~~~~~~~~~~~~~~~
    # (i) Get grid centroid
    grid_centre = gdf_grid.loc[gdf_grid['grid_250m']==select_grid].centroid
    centroid= geopandas.GeoDataFrame({'geometry':grid_centre})
    centroid = centroid.set_crs('EPSG:27700')

    #~~~~~~~~~~~~~~~
    # (ii) Get 4 corner points from grid polygon
    work_grid = gdf_grid.loc[gdf_grid['grid_250m']==select_grid].copy()
    diag_length = np.floor(np.sqrt(2*(work_grid.length/4.0).values[0]**2))
    work_grid.geometry = work_grid.geometry.apply(lambda x: MultiPoint(list(x.exterior.coords)))
    corner_points = work_grid.explode(index_parts=True).drop_duplicates() # four corner point coords of grid cell

    #~~~~~~~~~~~~~~~
    # (iii) Add 4 grid boundary mid points
    geom_90 = []
    for p1,p2 in list(itertools.product(corner_points['geometry'].values, corner_points['geometry'].values)): geom_90.append(LineString([p1,p2]))
    result_90= geopandas.GeoDataFrame({'geometry':geom_90})
    result_90 = result_90.set_crs('EPSG:27700')
    result_90['length'] = result_90.length
    outer_lines = result_90.loc[result_90['length']<diag_length] # remove the diagonals
    centroids = outer_lines.apply(lambda row: row['geometry'].centroid, axis=1)
    # 8 points (4 corner points + four boundary mid points)
    centroids_all = geopandas.GeoDataFrame({'geometry':centroids})
    centroids_all = centroids_all.drop_duplicates()
    centroids_all = centroids_all.set_crs('EPSG:27700')
    # sort by y coordinate (latitude)
    # pdb.set_trace()
    centroids_all = centroids_all.iloc[centroids_all.geometry.y.argsort().values[:]].reset_index()
    sequence = [10,8,6,12,4,14,0,2] # numbering to be able to distinguish line orientations easily
    df_seq = pd.DataFrame({'order':sequence})
    centroids_all_final = pd.concat([centroids_all, df_seq], axis=1)
    
    #~~~~~~~~~~~~~~~
    # (iv) Add additional 8 points to get 22.5 deg spacing
    alpha = angle_offset*np.pi/180.0  # angular spacing of transects
    # alpha is measured from the transects at right angles to the grid boundary (90 deg)

    # (a) need to determine the length of the transects
    geom_90_line = []
    for p1,p2 in list(itertools.product(centroids_all_final['geometry'].values, centroid['geometry'].values)): geom_90_line.append(LineString([p1,p2]))
    result_90_line= geopandas.GeoDataFrame({'geometry':geom_90_line})
    result_90_line = result_90_line.set_crs('EPSG:27700')
    result_90_line['length'] = result_90_line.length
    result_90_line = result_90_line.drop_duplicates(subset=['length'], keep='first')
    result_90_line = result_90_line.loc[result_90_line['length']<300]
    # average length (good enough approximation)
    len_90 = result_90_line['length'].mean()

    # (b) distance of new point at 22.5 from previous point
    dist = np.tan(alpha) * len_90

    # (c) determine coordinates of new 8 points
    # existing points
    p0 = centroids_all_final.loc[centroids_all_final['order']==0]
    x0 = p0['geometry'].values[0].coords.xy[0][0]
    y0 = p0['geometry'].values[0].coords.xy[1][0]
    p2 = centroids_all_final.loc[centroids_all_final['order']==2]
    x2 = p2['geometry'].values[0].coords.xy[0][0]
    y2 = p2['geometry'].values[0].coords.xy[1][0]
    p8 = centroids_all_final.loc[centroids_all_final['order']==8]
    x8 = p8['geometry'].values[0].coords.xy[0][0]
    y8 = p8['geometry'].values[0].coords.xy[1][0]
    p4 = centroids_all_final.loc[centroids_all_final['order']==4]
    x4 = p4['geometry'].values[0].coords.xy[0][0]
    y4 = p4['geometry'].values[0].coords.xy[1][0]
    p12 = centroids_all_final.loc[centroids_all_final['order']==12]
    x12 = p12['geometry'].values[0].coords.xy[0][0]
    y12 = p12['geometry'].values[0].coords.xy[1][0]

    # angular rotation of the entire grid
    beta = np.arctan((y2-y0)/(x2-x0))*180.0/np.pi

    # distances measured from points 0 and 8
    dy = np.sin(beta*np.pi/180.0) * dist
    dx = np.cos(beta*np.pi/180.0) * dist
    point_1 = Point([x0 + dx, y0 + dy])
    result_22_1 = geopandas.GeoDataFrame({'order':1,'geometry':point_1},index=[0])
    point_15 = Point([x0 - dx, y0 - dy])
    result_22_15 = geopandas.GeoDataFrame({'order':15,'geometry':point_15},index=[0])
    point_7 = Point([x8 + dx, y8 + dy])
    result_22_7 = geopandas.GeoDataFrame({'order':7,'geometry':point_7},index=[0])
    point_9 = Point([x8 - dx, y8 - dy])
    result_22_9 = geopandas.GeoDataFrame({'order':9,'geometry':point_9},index=[0])

    # distances measured from points 4 and 12
    dx = np.sin(beta*np.pi/180.0) * dist
    dy = np.cos(beta*np.pi/180.0) * dist
    point_3 = Point([x4 - dx, y4 + dy])
    result_22_3 = geopandas.GeoDataFrame({'order':3,'geometry':point_3},index=[0])
    point_5 = Point([x4 + dx, y4 - dy])
    result_22_5 = geopandas.GeoDataFrame({'order':5,'geometry':point_5},index=[0])
    point_13 = Point([x12 - dx, y12 + dy])
    result_22_13 = geopandas.GeoDataFrame({'order':13,'geometry':point_13},index=[0])
    point_11 = Point([x12 + dx, y12 - dy])
    result_22_11 = geopandas.GeoDataFrame({'order':11,'geometry':point_11},index=[0])

    # combine results
    all_22 = pd.concat([result_22_1,result_22_15,result_22_7,result_22_9,result_22_3,result_22_5,result_22_13,result_22_11])
    all_22 = all_22.set_crs('EPSG:27700')
    all_points = pd.concat([centroids_all_final,all_22]) # all 16 points on grid boundary
    all_points = all_points.reset_index() 

    #~~~~~~~~~~~~~~~
    # (v) Create 16 linestrings from boundary points to grid centroid
    geom_all = []
    order_list = all_points['order'].values
    for p1,p2 in list(itertools.product(all_points['geometry'].values, centroid['geometry'].values)): geom_all.append(LineString([p1,p2]))
    all_transects= geopandas.GeoDataFrame({'order':order_list, 'geometry':geom_all})
    all_transects = all_transects.set_crs('EPSG:27700')
    all_transects['length'] = all_transects.length
    # all_transects.to_file('./output/temp/all_FAI_transects.shp')
    
    #~~~~~~~~~~~~~~~
    # (vi) extract building information on transects
    inters_bldgs = []
    inters_len   = []
    for i in range(16):
        a, b = extract_polygons(all_transects.loc[all_transects['order']==i], gdf_bldgs)
        inters_bldgs.append(a)
        inters_len.append(b)
    
    #~~~~~~~~~~~~~~~
    # (vii) compute fai (2 ways)
    fai_m = [] # multiple building encounters possible
    fai_s = [] # single building encounters only
    for i in range(16):
        transect_length = all_transects.loc[all_transects['order']==i]['length'].values[0]
        fai_m.append(((inters_bldgs[i]['height'] * inters_bldgs[i]['n_inters']).sum()) / transect_length)
        fai_s.append(((inters_bldgs[i]['height']).sum()) / transect_length)
    return fai_m, fai_s


#___________________________________________________________________________________________
# current time
release_date = datetime.today().strftime('%Y-%m-%d %H:%m')

#______________________________
BRTYND_domain = geopandas.read_file('../input/BRTYND_grid/BRTYND_grid_27700.shp')
BRTYND_domain["release"] = release_date
BRTYND_domain['ref_year']  = '03/2023'
BRTYND_domain["grid_a_m2"] = BRTYND_domain.area
BRTYND_domain['grid_250m'] = 'grid_250m'
# Initialize FAI columns by wind sector
for i in range(16):
    BRTYND_domain[f"fai_m_{i}"] = 0.0  # multiple encounters
for i in range(16):
    BRTYND_domain[f"fai_s_{i}"] = 0.0  # single encounters
# Initialize average FAI 
BRTYND_domain["fai_m_ave"] = 0.0
BRTYND_domain["fai_s_ave"] = 0.0

# Import building polygon data in domain
# This is the output of BRTYND_buildings_prepare.py
gdf_bldgs = geopandas.read_file('./output/temp/gdf_bldgs_in_BRTYND_grid_buffered.shp')

# Heights
gdf_bldgs['height'] = gdf_bldgs['relh2']

# list of grids in processing subregions
grids_in_sr = gdf_bldgs["grid_250m"].unique().tolist()

for idx, row in BRTYND_domain.iterrows():
    # Compute morphology parameters
    fai_m_out, fai_s_out = compute_fai(BRTYND_domain, gdf_bldgs, row["grid_250m"], 22.5)
    
    # Save data to grid gdf
    BRTYND_domain.loc[idx,'fai_m_ave']  = np.mean(fai_m_out)
    BRTYND_domain.loc[idx,'fai_s_ave']  = np.mean(fai_s_out)
    for j in range(16):
        BRTYND_domain.loc[idx,'fai_m_%s'%j] = fai_m_out[j]
        BRTYND_domain.loc[idx,'fai_s_%s'%j] = fai_s_out[j]

print("Saving output...")
BRTYND_domain = BRTYND_domain.drop(columns=['id', 'geometry'])
BRTYND_domain.to_csv(f"./output/BRTYND_building_FAI.csv", index=False)
