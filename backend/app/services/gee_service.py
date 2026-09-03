try:
    import ee
    GEE_AVAILABLE = True
except ImportError:
    ee = None
    GEE_AVAILABLE = False

import json
from typing import Dict, Any

FLORES_BBOX = None

# Realistic potential zones on Flores Island (alluvial river valleys, plains)
FALLBACK_GROUNDWATER_POTENTIAL = {
    "type": "FeatureCollection",
    "features": [
        {
            "type": "Feature",
            "properties": {
                "name": "Dataran Alluvial Maumere (High Potential)",
                "potential_score": 0.88,
                "aquifer_type": "Alluvial unconfined aquifer",
                "recommended_depth": "25-45m"
            },
            "geometry": {
                "type": "Polygon",
                "coordinates": [[
                    [122.10, -8.68],
                    [122.35, -8.68],
                    [122.35, -8.58],
                    [122.10, -8.58],
                    [122.10, -8.68]
                ]]
            }
        },
        {
            "type": "Feature",
            "properties": {
                "name": "Lembah Sungai Wae Ces - Ruteng (High Potential)",
                "potential_score": 0.82,
                "aquifer_type": "Volcanic fractured rock aquifer",
                "recommended_depth": "40-70m"
            },
            "geometry": {
                "type": "Polygon",
                "coordinates": [[
                    [120.40, -8.65],
                    [120.55, -8.65],
                    [120.55, -8.55],
                    [120.40, -8.55],
                    [120.40, -8.65]
                ]]
            }
        },
        {
            "type": "Feature",
            "properties": {
                "name": "Cekungan Ende (High Potential)",
                "potential_score": 0.79,
                "aquifer_type": "Coastal alluvial aquifer",
                "recommended_depth": "20-40m"
            },
            "geometry": {
                "type": "Polygon",
                "coordinates": [[
                    [121.60, -8.88],
                    [121.72, -8.88],
                    [121.72, -8.80],
                    [121.60, -8.80],
                    [121.60, -8.88]
                ]]
            }
        },
        {
            "type": "Feature",
            "properties": {
                "name": "Dataran Mbay / Nagekeo (High Potential)",
                "potential_score": 0.85,
                "aquifer_type": "Alluvial basin with high recharge",
                "recommended_depth": "30-55m"
            },
            "geometry": {
                "type": "Polygon",
                "coordinates": [[
                    [121.20, -8.60],
                    [121.35, -8.60],
                    [121.35, -8.50],
                    [121.20, -8.50],
                    [121.20, -8.60]
                ]]
            }
        },
        {
            "type": "Feature",
            "properties": {
                "name": "Larantuka Coastal Plain (Moderate-High Potential)",
                "potential_score": 0.75,
                "aquifer_type": "Volcanic foot-slope aquifer",
                "recommended_depth": "35-60m"
            },
            "geometry": {
                "type": "Polygon",
                "coordinates": [[
                    [122.95, -8.40],
                    [123.05, -8.40],
                    [123.05, -8.30],
                    [122.95, -8.30],
                    [122.95, -8.40]
                ]]
            }
        }
    ]
}

def initialize_gee(service_account: str, key_file: str, project_id: str):
    """Initializes Google Earth Engine with service account credentials."""
    global FLORES_BBOX
    if not GEE_AVAILABLE:
        print("earthengine-api is not installed. Using simulated geospatial layers.")
        return
    try:
        credentials = ee.ServiceAccountCredentials(service_account, key_file)
        ee.Initialize(credentials, project=project_id)
        FLORES_BBOX = ee.Geometry.BBox(119.5, -9.0, 123.5, -8.0)
        print("Google Earth Engine initialized successfully.")
    except Exception as e:
        print(f"Failed to initialize GEE: {e}. Using fallback layers.")

def get_elevation_tiles() -> dict:
    if not GEE_AVAILABLE or not FLORES_BBOX:
        # Fallback to public global elevation tiles or empty
        return {"tile_url": "https://s3.amazonaws.com/elevation-tiles-prod/terrarium/{z}/{x}/{y}.png"}
    try:
        dem = ee.Image('USGS/SRTMGL1_003').clip(FLORES_BBOX)
        vis_params = {'min': 0, 'max': 3000, 'palette': ['006600', '002200', 'fff700', 'ab7634', 'c4d0ff', 'ffffff']}
        map_id_dict = dem.getMapId(vis_params)
        return {"tile_url": map_id_dict['tile_fetcher'].url_format}
    except Exception:
        return {"tile_url": "https://s3.amazonaws.com/elevation-tiles-prod/terrarium/{z}/{x}/{y}.png"}

def get_ndvi_tiles() -> dict:
    if not GEE_AVAILABLE or not FLORES_BBOX:
        return {"tile_url": ""}
    try:
        s2 = ee.ImageCollection('COPERNICUS/S2_SR_HARMONIZED').filterBounds(FLORES_BBOX).filterDate('2024-01-01', '2024-12-31')
        median_s2 = s2.median().clip(FLORES_BBOX)
        ndvi = median_s2.normalizedDifference(['B8', 'B4'])
        map_id_dict = ndvi.getMapId({'min': -0.2, 'max': 0.8, 'palette': ['FFFFFF', 'CE7E45', 'DF923D', 'F1B555', 'FCD163', '99B718', '74A901', '66A000', '529400', '3E8601', '207401', '056201', '004C00']})
        return {"tile_url": map_id_dict['tile_fetcher'].url_format}
    except Exception:
        return {"tile_url": ""}

def get_moisture_tiles() -> dict:
    if not GEE_AVAILABLE or not FLORES_BBOX:
        return {"tile_url": ""}
    try:
        s2 = ee.ImageCollection('COPERNICUS/S2_SR_HARMONIZED').filterBounds(FLORES_BBOX).filterDate('2024-01-01', '2024-12-31')
        median_s2 = s2.median().clip(FLORES_BBOX)
        ndmi = median_s2.normalizedDifference(['B8', 'B11'])
        map_id_dict = ndmi.getMapId({'min': -0.2, 'max': 0.6, 'palette': ['d73027', 'fc8d59', 'fee090', 'e0f3f8', '91bfdb', '4575b4']})
        return {"tile_url": map_id_dict['tile_fetcher'].url_format}
    except Exception:
        return {"tile_url": ""}

def get_groundwater_potential() -> dict:
    if not GEE_AVAILABLE or not FLORES_BBOX:
        return FALLBACK_GROUNDWATER_POTENTIAL
    try:
        dem = ee.Image('USGS/SRTMGL1_003').clip(FLORES_BBOX)
        slope = ee.Terrain.slope(dem)
        slope_norm = ee.Image(1).subtract(slope.divide(90))
        s2 = ee.ImageCollection('COPERNICUS/S2_SR_HARMONIZED').filterBounds(FLORES_BBOX).filterDate('2024-01-01', '2024-12-31')
        median_s2 = s2.median().clip(FLORES_BBOX)
        ndvi = median_s2.normalizedDifference(['B8', 'B4']).add(1).divide(2)
        ndmi = median_s2.normalizedDifference(['B8', 'B11']).add(1).divide(2)
        potential = slope_norm.multiply(0.3).add(ndvi.multiply(0.3)).add(ndmi.multiply(0.4)).gt(0.6)
        
        map_id_dict = potential.selfMask().getMapId({
            'min': 1, 'max': 1, 
            'palette': ['059669']  # Emerald green for high potential
        })
        return {"tile_url": map_id_dict['tile_fetcher'].url_format, "type": "raster"}
    except Exception as e:
        print(f"GEE Potential Error: {e}")
        return FALLBACK_GROUNDWATER_POTENTIAL
