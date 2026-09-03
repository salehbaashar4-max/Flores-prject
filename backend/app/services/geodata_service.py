from typing import Dict, Any
from app.services.osm_service import fetch_rivers as fetch_osm_rivers

def get_cat_basins() -> Dict[str, Any]:
    return {
        "type": "FeatureCollection",
        "features": []
    }

def get_geology() -> Dict[str, Any]:
    return {
        "type": "FeatureCollection",
        "features": []
    }

def get_rivers() -> Dict[str, Any]:
    return fetch_osm_rivers()
