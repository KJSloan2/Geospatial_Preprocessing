import os
import json
import zipfile
import shutil
import geopandas as gpd
import pyproj as proj
from pyproj import Transformer
import fiona
import re
######################################################################################
######################################################################################
# provide the folder name and the shapefile zip names to process
queryFolderName = "tiger"
#shapefileZipNames = ["ASC_Art_Installations", "Churches", "Colleges", "Common_Area_Parcels", "Discgolf_Fairway", "Discgolf_Tees", "Golf_Courses", "Greenway_Entrances", "GreenwayMasterPlan", "Greenways"]
shapefileZipNames = ['tl_2024_48_elsd']
######################################################################################
script_dir = os.path.dirname(os.path.abspath(__file__))
split_dir = str(script_dir).split("\\")
idx_src = split_dir.index("src")
parent_dir = os.path.abspath(os.path.join(script_dir, ".."))
######################################################################################
######################################################################################
crsRefJson = json.load(open(os.path.join("data", 'reference', "crs_ref.json")))

crsRef = {"epsg":[], "crs_name":[], "prj_crs":[]}
for item in crsRefJson:
    crsRef["epsg"].append(item["epsg"])
    crsRef["crs_name"].append(item["crs_name"])
    crsRef["prj_crs"].append(item["prj_crs"])  
######################################################################################
def list_folders(directory):
    try:
        # List only directories
        folders = [f for f in os.listdir(directory) if os.path.isdir(os.path.join(directory, f))]
        return folders
    except FileNotFoundError:
        return f"Error: The directory '{directory}' does not exist."
    except PermissionError:
        return f"Error: Permission denied for directory '{directory}'."
######################################################################################
def create_folder(path):
    try:
        os.makedirs(path, exist_ok=True)  # Creates the folder and any intermediate folders if needed
        print(f"Folder '{path}' created successfully!")
    except PermissionError:
        print(f"Error: Permission denied for creating folder '{path}'.")
    except FileExistsError:
        print(f"Error: Folder '{path}' already exists.")
    except Exception as e:
        print(f"An unexpected error occurred: {e}")
######################################################################################
######################################################################################

def list_files_in_directory(directory_path: str):
    try:
        # Get a list of all files in the given directory
        files = [file for file in os.listdir(directory_path) if os.path.isfile(os.path.join(directory_path, file))]
        return files
    except FileNotFoundError:
        print(f"The directory {directory_path} does not exist.")
        return []
    except PermissionError:
        print(f"Permission denied for accessing {directory_path}.")
        return []

if len(shapefileZipNames) == 0:
    files = list_files_in_directory(os.path.join(r"data", queryFolderName))
    for f in files:
        if f.endswith('.zip'):
           shapefileZipNames.append(f.split(".")[0])

def read_prj(prj_file_path):
    try:
        with open(prj_file_path, 'r', encoding='utf-8') as prj_file:
            prj_content = prj_file.read()
        return prj_content
    except Exception as e:
        print(f"Error reading .prj file: {e}")
        return None
    
def parse_prj(prj_content):
    try:
        # Extract GCS name
        gcs_match = re.search(r'GEOGCS\["([^"]+)"', prj_content)
        gcs_name = gcs_match.group(1) if gcs_match else None

        # Extract DATUM name
        datum_match = re.search(r'DATUM\["([^"]+)"', prj_content)
        datum_name = datum_match.group(1) if datum_match else None

        return gcs_name, datum_name
    except Exception as e:
        print(f"Error parsing .prj content: {e}")
        return None, None
######################################################################################
folders = list_folders(os.path.join(parent_dir, "output"))
if queryFolderName not in folders:
    folder_path = os.path.join(parent_dir, "output", queryFolderName)
    create_folder(folder_path)

for shapefileZipName in shapefileZipNames:

    zip_file_path =  os.path.join(parent_dir, "data", queryFolderName, shapefileZipName+".zip")
    geojson_output_path = os.path.join(parent_dir, "output", queryFolderName, shapefileZipName+".geojson")
    #print(zip_file_path, geojson_output_path)
    
    def shapefile_to_geojson(zip_path, output_geojson_path):
        epsgCode = None  # Initialize epsgCode to None
        try:
            print(f"{shapefileZipName} is being processed...")
            # Open the ZIP file
            with zipfile.ZipFile(zip_path, 'r') as zip_ref:
                # List all files in the ZIP (including those in subfolders)
                all_files = zip_ref.namelist()
                
                # Find the .shp file (including in subfolders)
                shp_file_name = next((f for f in all_files if f.endswith('.shp')), None)
                prj_file_name = next((f for f in all_files if f.endswith('.prj')), None)
            
                if not shp_file_name:
                    raise FileNotFoundError(
                        "No .shp file found in the provided .zip archive.")
                
                # Get the directory path of the .shp file
                shp_dir = os.path.dirname(shp_file_name)
                base_name = os.path.splitext(os.path.basename(shp_file_name))[0]
                
                # Extract all related files
                shp_related_files = [
                    f for f in all_files if 
                    os.path.basename(f).startswith(base_name)
                ]
                
                temp_extract_dir = os.path.join(parent_dir, "data", queryFolderName, "temp_extract")
                os.makedirs(temp_extract_dir, exist_ok=True)

                # Read data from prj
                if prj_file_name:
                    zip_ref.extract(prj_file_name, temp_extract_dir)
                    prj_file_path = os.path.join(temp_extract_dir, prj_file_name)
                    prj_content = read_prj(prj_file_path)

                    gcsName = parse_prj(prj_content)[0]
                    print(f"CRS GCS Name: {gcsName}")
                    if gcsName in crsRef["crs_name"]:
                        idx_gcsName = crsRef["crs_name"].index(gcsName)
                        epsgCode = crsRef["epsg"][idx_gcsName]
                        print(epsgCode)
                    else:
                        print(f"CRS {gcsName} not found")
                        #epsgCode = 4326

                for file in shp_related_files:
                    zip_ref.extract(file, temp_extract_dir)

                # Build the full path to the extracted .shp file
                shp_file_path = os.path.join(temp_extract_dir, shp_file_name)
                
                # Read the shapefile using GeoPandas
                gdf = gpd.read_file(shp_file_path)
                
                # Convert to GeoJSON and save
                gdf.to_file(output_geojson_path, driver='GeoJSON')
        
        finally:
            # Ensure the extracted temporary directory is removed
            if os.path.exists("temp_extract"):
                shutil.rmtree("temp_extract")
        return epsgCode

    epsgCode = shapefile_to_geojson(zip_file_path, geojson_output_path)
    print(f"{shapefileZipName} has been converted to GeoJSON")
    ##################################################################################
    if epsgCode is not None:
        transformer = Transformer.from_crs(
            proj.CRS(f'epsg:{epsgCode}'), proj.CRS('epsg:4326'), always_xy=True)

        output = {
            "type": "FeatureCollection",
            "features": []
        }

        with fiona.open(geojson_output_path, mode="r") as src:
            print("Total Features:", len(src))
            print("Schema:", src.schema)

            # Iterate through features
            for feature in src:
                try:
                    properties = {}
                    for key, value in feature["properties"].items():
                        properties[key] = value

                    geometry = feature["geometry"]
                    newFeature = {
                        "type": "Feature",
                        "properties": properties,
                        "geometry": {
                            "type": geometry["type"],
                            "coordinates": []
                        }
                    }
                    ##########################################################################
                    #print(geometry["type"], geometry["coordinates"])
                    '''if geometry["type"] in ["Polygon", "MultiPolygon"]:
                        # Transform all coordinate rings (exterior and any holes)
                        coordinates = geometry["coordinates"]
                        poolCoords = [[],[]]
                        for ring in coordinates:
                            transformed_ring = [
                                transformer.transform(coord[0], coord[1]) for coord in ring
                            ]
                            #print("Transformed Ring (EPSG:4326):", transformed_ring)
                            for coord in transformed_ring:
                                poolCoords[0].append(coord[0])
                                poolCoords[1].append(coord[1])
                            newFeature["geometry"]["coordinates"].append(transformed_ring)
                        
                        centroid = [
                            sum(poolCoords[1])/len(poolCoords[1]), 
                            sum(poolCoords[0])/len(poolCoords[0])]
                        
                        newFeature["properties"]["centroid"] = centroid
                        output["features"].append(newFeature)'''
                    
                    if geometry["type"] == "Polygon":
                        # A Polygon has a single list of rings
                        poolCoords = [[], []]
                        transformed_polygon = []
                        for ring in geometry["coordinates"]:
                            transformed_ring = [
                                transformer.transform(coord[0], coord[1]) for coord in ring
                            ]
                            for coord in transformed_ring:
                                poolCoords[0].append(coord[0])
                                poolCoords[1].append(coord[1])
                            transformed_polygon.append(transformed_ring)
                        newFeature["geometry"]["coordinates"] = transformed_polygon

                        centroid = [
                            sum(poolCoords[1]) / len(poolCoords[1]),
                            sum(poolCoords[0]) / len(poolCoords[0])
                        ]

                        newFeature["properties"]["centroid"] = centroid
                        output["features"].append(newFeature)

                    elif geometry["type"] == "MultiPolygon":
                        # A MultiPolygon has multiple lists of polygons
                        poolCoords = [[], []]
                        transformed_multipolygon = []
                        for polygon in geometry["coordinates"]:
                            transformed_polygon = []
                            for ring in polygon:
                                transformed_ring = [
                                    transformer.transform(coord[0], coord[1]) for coord in ring
                                ]
                                for coord in transformed_ring:
                                    poolCoords[0].append(coord[0])
                                    poolCoords[1].append(coord[1])
                                transformed_polygon.append(transformed_ring)
                            transformed_multipolygon.append(transformed_polygon)
                        newFeature["geometry"]["coordinates"] = transformed_multipolygon

                        centroid = [
                            sum(poolCoords[1]) / len(poolCoords[1]),
                            sum(poolCoords[0]) / len(poolCoords[0])
                        ]

                        newFeature["properties"]["centroid"] = centroid
                        output["features"].append(newFeature)
                    elif geometry["type"] == "LineString":
                        # Transform all coordinate rings (exterior and any holes)
                        coordinates = geometry["coordinates"]
                        poolCoords = [[],[]]
                        transformed_linestring = []
                        for coord in coordinates:
                            transformed_coordinates = transformer.transform(coord[0], coord[1])
                            poolCoords[0].append(transformed_coordinates[0])
                            poolCoords[1].append(transformed_coordinates[1])
                            transformed_linestring.append(transformed_coordinates)
                        newFeature["geometry"]["coordinates"] = transformed_linestring
                        
                        centroid = [
                            sum(poolCoords[1])/len(poolCoords[1]), 
                            sum(poolCoords[0])/len(poolCoords[0])]
                        
                        newFeature["properties"]["centroid"] = centroid
                        output["features"].append(newFeature)

                    elif geometry["type"] == "Point":
                        coordinates = geometry["coordinates"]
                        transformed_coordinates = transformer.transform(coordinates[0], coordinates[1])
                        newFeature["properties"]["centroid"] = [transformed_coordinates[0], transformed_coordinates[1]]
                        newFeature["geometry"]["coordinates"] = [transformed_coordinates[0], transformed_coordinates[1]]
                        output["features"].append(newFeature)
                except Exception as e:
                    print(e)
                    pass

        try:
            with open(os.path.join(parent_dir, "output", shapefileZipName+".geojson"), "w", encoding='utf-8') as output_json:
                output_json.write(json.dumps(output, indent=1, ensure_ascii=False))
            print(f"{shapefileZipName} : transformed to EPSG:4326")
        except Exception as e:
            print(e)
            pass
    else:
        print(f"{shapefileZipName} : No EPSG code found, skipping transformation to EPSG:4326")
        continue

print('DONE')