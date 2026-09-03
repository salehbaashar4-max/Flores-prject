import requests
import json
import time
from typing import Dict, Any

# Multiple mirrors — tried in order until one succeeds.
OVERPASS_MIRRORS = [
    "https://overpass-api.de/api/interpreter",
    "https://overpass.kumi.systems/api/interpreter",
    "https://maps.mail.ru/osm/tools/overpass/api/interpreter",
]

# A descriptive User-Agent is REQUIRED: overpass-api.de returns HTTP 406 without one.
OVERPASS_HEADERS = {
    "User-Agent": "FloresGroundwaterDashboard/1.0 (hydrogeology research; contact: admin@flores.local)",
    "Accept": "application/json",
}

# Realistic fallback dataset for Flores Island if Overpass API fails/times out
FALLBACK_RESTRICTED_ZONES = {
    "type": "FeatureCollection",
    "features": [
        {
            "type": "Feature",
            "properties": {
                "name": "Taman Nasional Kelimutu (Kelimutu National Park)",
                "type": "protected_area"
            },
            "geometry": {
                "type": "Polygon",
                "coordinates": [[
                    [121.78, -8.78],
                    [121.85, -8.78],
                    [121.85, -8.74],
                    [121.78, -8.74],
                    [121.78, -8.78]
                ]]
            }
        },
        {
            "type": "Feature",
            "properties": {
                "name": "Taman Wisata Alam 17 Pulau Riung (Riung 17 Islands Nature Park)",
                "type": "protected_area"
            },
            "geometry": {
                "type": "Polygon",
                "coordinates": [[
                    [120.95, -8.45],
                    [121.10, -8.45],
                    [121.10, -8.38],
                    [120.95, -8.38],
                    [120.95, -8.45]
                ]]
            }
        },
        {
            "type": "Feature",
            "properties": {
                "name": "Taman Nasional Komodo (Komodo National Park - East Sector)",
                "type": "protected_area"
            },
            "geometry": {
                "type": "Polygon",
                "coordinates": [[
                    [119.65, -8.70],
                    [119.85, -8.70],
                    [119.85, -8.45],
                    [119.65, -8.45],
                    [119.65, -8.70]
                ]]
            }
        },
        {
            "type": "Feature",
            "properties": {
                "name": "TPU Ruteng (Ruteng Public Cemetery)",
                "type": "cemetery"
            },
            "geometry": {
                "type": "Polygon",
                "coordinates": [[
                    [120.46, -8.62],
                    [120.48, -8.62],
                    [120.48, -8.60],
                    [120.46, -8.60],
                    [120.46, -8.62]
                ]]
            }
        },
        {
            "type": "Feature",
            "properties": {
                "name": "Makam Pahlawan Maumere (Maumere Cemetery)",
                "type": "cemetery"
            },
            "geometry": {
                "type": "Polygon",
                "coordinates": [[
                    [122.20, -8.62],
                    [122.22, -8.62],
                    [122.22, -8.60],
                    [122.20, -8.60],
                    [122.20, -8.62]
                ]]
            }
        },
        {
            "type": "Feature",
            "properties": {
                "name": "Kompleks Militer Kodim 1603/Sikka",
                "type": "military"
            },
            "geometry": {
                "type": "Polygon",
                "coordinates": [[
                    [122.21, -8.64],
                    [122.23, -8.64],
                    [122.23, -8.63],
                    [122.21, -8.63],
                    [122.21, -8.64]
                ]]
            }
        }
    ]
}

def fetch_restricted_zones() -> Dict[str, Any]:
    """Fetches restricted zones from Overpass API with local fallback on error."""
    query = """
    [out:json][timeout:60];
    (
      nwr["amenity"="grave_yard"](-9.0, 119.5, -8.0, 123.5);
      nwr["landuse"="cemetery"](-9.0, 119.5, -8.0, 123.5);
      nwr["boundary"="protected_area"](-9.0, 119.5, -8.0, 123.5);
      nwr["boundary"="national_park"](-9.0, 119.5, -8.0, 123.5);
      nwr["landuse"="military"](-9.0, 119.5, -8.0, 123.5);
      nwr["military"](-9.0, 119.5, -8.0, 123.5);
    );
    out geom;
    """

    # Try each mirror; one retry per mirror on transient failure.
    for mirror in OVERPASS_MIRRORS:
        for attempt in range(2):
            try:
                response = requests.post(
                    mirror,
                    data={"data": query},
                    headers=OVERPASS_HEADERS,
                    timeout=70,
                )
                response.raise_for_status()
                data = response.json()
                result = overpass_to_geojson(data)
                if result.get("features"):
                    print(f"Overpass OK via {mirror}: {len(result['features'])} restricted zones.")
                    return result
                break
            except (requests.RequestException, ValueError) as e:
                print(f"Overpass Error on {mirror} (Attempt {attempt+1}): {e}")
                time.sleep(2)

    print("Falling back to local static restricted zones.")
    return FALLBACK_RESTRICTED_ZONES

def fetch_rivers() -> Dict[str, Any]:
    """Fetches real rivers and waterways from Overpass API."""
    query = """
    [out:json][timeout:60];
    (
      way["waterway"="river"](-9.0, 119.5, -8.0, 123.5);
      way["waterway"="stream"](-9.0, 119.5, -8.0, 123.5);
    );
    out geom;
    """
    for mirror in OVERPASS_MIRRORS:
        for attempt in range(2):
            try:
                response = requests.post(
                    mirror,
                    data={"data": query},
                    headers=OVERPASS_HEADERS,
                    timeout=70,
                )
                response.raise_for_status()
                data = response.json()
                result = overpass_to_geojson(data)
                if result.get("features"):
                    print(f"Overpass OK via {mirror}: {len(result['features'])} rivers.")
                    return result
                break
            except (requests.RequestException, ValueError) as e:
                print(f"Overpass Error on {mirror} (Attempt {attempt+1}): {e}")
                time.sleep(2)
    return {"type": "FeatureCollection", "features": []}

def overpass_to_geojson(data: Dict[str, Any]) -> Dict[str, Any]:
    """Converts Overpass JSON to a GeoJSON FeatureCollection."""
    features = []
    
    for element in data.get("elements", []):
        feature = {
            "type": "Feature",
            "properties": {},
            "geometry": {}
        }
        
        tags = element.get("tags", {})
        feature["properties"]["name"] = tags.get("name", "Unknown")
        feature["properties"]["source_tags"] = tags
        
        if "amenity" in tags and tags["amenity"] == "grave_yard":
            feature["properties"]["type"] = "cemetery"
        elif "landuse" in tags and tags["landuse"] == "cemetery":
            feature["properties"]["type"] = "cemetery"
        elif "boundary" in tags and tags["boundary"] in ["protected_area", "national_park"]:
            feature["properties"]["type"] = "protected_area"
        elif ("landuse" in tags and tags["landuse"] == "military") or "military" in tags:
            feature["properties"]["type"] = "military"
        else:
            feature["properties"]["type"] = "unknown"
            
        elem_type = element.get("type")
        if elem_type == "node":
            feature["geometry"] = {
                "type": "Point",
                "coordinates": [element.get("lon"), element.get("lat")]
            }
        elif elem_type == "way":
            geometry = element.get("geometry", [])
            coords = [[pt.get("lon"), pt.get("lat")] for pt in geometry]
            if len(coords) >= 4 and coords[0] == coords[-1]:
                feature["geometry"] = {
                    "type": "Polygon",
                    "coordinates": [coords]
                }
            else:
                feature["geometry"] = {
                    "type": "LineString",
                    "coordinates": coords
                }
        elif elem_type == "relation":
            members = element.get("members", [])
            polygons = []
            for member in members:
                if member.get("type") == "way" and "geometry" in member:
                    coords = [[pt.get("lon"), pt.get("lat")] for pt in member.get("geometry", [])]
                    if len(coords) >= 4 and coords[0] == coords[-1]:
                        polygons.append([coords])
            
            feature["geometry"] = {
                "type": "MultiPolygon",
                "coordinates": polygons
            }
        
        if feature["geometry"]:
            features.append(feature)
            
    return {
        "type": "FeatureCollection",
        "features": features
    }
