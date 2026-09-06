from typing import Dict, Any
from app.services.osm_service import fetch_rivers as fetch_osm_rivers

def get_cat_basins() -> Dict[str, Any]:
    return {
        "type": "FeatureCollection",
        "features": [
            {
                "type": "Feature",
                "properties": {
                    "name_id": "CAT Maumere",
                    "name_ar": "حوض ماوميري",
                    "type": "Sedimentary / Alluvial",
                    "productivity": "High (15-20 L/s)"
                },
                "geometry": {
                    "type": "Polygon",
                    "coordinates": [[[122.10, -8.65], [122.35, -8.65], [122.35, -8.55], [122.10, -8.55], [122.10, -8.65]]]
                }
            },
            {
                "type": "Feature",
                "properties": {
                    "name_id": "CAT Ruteng",
                    "name_ar": "حوض روتنغ",
                    "type": "Fractured Volcanic",
                    "productivity": "Medium-High (10-15 L/s)"
                },
                "geometry": {
                    "type": "Polygon",
                    "coordinates": [[[120.40, -8.68], [120.55, -8.68], [120.55, -8.55], [120.40, -8.55], [120.40, -8.68]]]
                }
            },
            {
                "type": "Feature",
                "properties": {
                    "name_id": "CAT Ende",
                    "name_ar": "حوض إيندي",
                    "type": "Volcanic / Sedimentary Mix",
                    "productivity": "Medium (5-10 L/s)"
                },
                "geometry": {
                    "type": "Polygon",
                    "coordinates": [[[121.55, -8.90], [121.75, -8.90], [121.75, -8.75], [121.55, -8.75], [121.55, -8.90]]]
                }
            }
        ]
    }

def get_geology() -> Dict[str, Any]:
    return {
        "type": "FeatureCollection",
        "features": [
            {
                "type": "Feature",
                "properties": {
                    "name_id": "Vulkanik Kuarter (Qv)",
                    "name_ar": "صخور بركانية حديثة",
                    "rock_type": "Basalt, Andesite, Tuff"
                },
                "geometry": {
                    "type": "Polygon",
                    "coordinates": [[[119.8, -9.0], [121.0, -9.0], [121.0, -8.4], [119.8, -8.4], [119.8, -9.0]]]
                }
            },
            {
                "type": "Feature",
                "properties": {
                    "name_id": "Aluvium (Qa)",
                    "name_ar": "رواسب طميية ونهرية",
                    "rock_type": "Sand, Gravel, Clay"
                },
                "geometry": {
                    "type": "Polygon",
                    "coordinates": [[[122.0, -8.7], [123.0, -8.7], [123.0, -8.3], [122.0, -8.3], [122.0, -8.7]]]
                }
            }
        ]
    }

def get_rivers() -> Dict[str, Any]:
    return fetch_osm_rivers()
