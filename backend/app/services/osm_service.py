"""OpenStreetMap (Overpass API) data for Flores and the neighbouring islands.

Two layers are served from here, and keeping them apart is the whole point:

  * restricted zones — where drilling is genuinely not allowed: military land,
    cemeteries, and airport airside.
  * protected areas — national parks and nature reserves. These are permit
    zones, not drilling bans, and they contain inhabited villages that need
    wells. Painting a whole island red because a park boundary crosses it is
    wrong, so they live behind their own endpoint and their own toggle.

Nothing here is invented. If Overpass cannot be reached the response is an
empty FeatureCollection tagged source="unavailable", so the map can say so
rather than draw placeholder rectangles.
"""
import time
from typing import Any, Dict, List

import requests

# Flores + Komodo/Rinca, Lembata, Adonara, Solor and the small islands between.
BBOX = "-9.30,119.00,-7.80,124.30"

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

# Tags kept on each feature. Everything else in the OSM tag soup is dropped so the
# payload stays small enough for a serverless response.
KEPT_TAGS = (
    "name", "name:id", "operator", "protect_class", "protection_title",
    "military", "aeroway", "landuse", "boundary", "leisure", "amenity",
)

RESTRICTED_QUERY = f"""
[out:json][timeout:50];
(
  nwr["amenity"="grave_yard"]({BBOX});
  nwr["landuse"="cemetery"]({BBOX});
  nwr["landuse"="military"]({BBOX});
  nwr["military"]({BBOX});
  nwr["aeroway"="aerodrome"]({BBOX});
);
out geom;
"""

PROTECTED_QUERY = f"""
[out:json][timeout:50];
(
  nwr["boundary"="protected_area"]({BBOX});
  nwr["boundary"="national_park"]({BBOX});
  nwr["leisure"="nature_reserve"]({BBOX});
);
out geom;
"""

RIVERS_QUERY = f"""
[out:json][timeout:50];
(
  way["waterway"="river"]({BBOX});
  way["waterway"="stream"]({BBOX});
);
out geom;
"""

EMPTY = {"type": "FeatureCollection", "features": [], "source": "unavailable"}


def _classify(tags: Dict[str, str]) -> str:
    """Map OSM tags onto the categories the legend uses."""
    if tags.get("amenity") == "grave_yard" or tags.get("landuse") == "cemetery":
        return "cemetery"
    if tags.get("landuse") == "military" or "military" in tags:
        return "military"
    if tags.get("aeroway") == "aerodrome":
        return "airport"
    if tags.get("boundary") in ("protected_area", "national_park"):
        return "protected_area"
    if tags.get("leisure") == "nature_reserve":
        return "nature_reserve"
    return "other"


def overpass_to_geojson(data: Dict[str, Any]) -> Dict[str, Any]:
    """Convert an Overpass JSON response into a GeoJSON FeatureCollection."""
    features: List[Dict[str, Any]] = []

    for element in data.get("elements", []):
        tags = element.get("tags", {})
        props: Dict[str, Any] = {
            "name": tags.get("name") or tags.get("name:id") or "Tanpa nama",
            "type": _classify(tags),
        }
        for key in KEPT_TAGS:
            if key in tags and key not in ("name", "name:id"):
                props[key] = tags[key]

        geometry: Dict[str, Any] = {}
        elem_type = element.get("type")

        if elem_type == "node":
            geometry = {
                "type": "Point",
                "coordinates": [element.get("lon"), element.get("lat")],
            }
        elif elem_type == "way":
            coords = [[pt.get("lon"), pt.get("lat")] for pt in element.get("geometry", [])]
            if len(coords) >= 4 and coords[0] == coords[-1]:
                geometry = {"type": "Polygon", "coordinates": [coords]}
            elif len(coords) >= 2:
                geometry = {"type": "LineString", "coordinates": coords}
        elif elem_type == "relation":
            polygons = []
            for member in element.get("members", []):
                if member.get("type") != "way" or "geometry" not in member:
                    continue
                coords = [[pt.get("lon"), pt.get("lat")] for pt in member.get("geometry", [])]
                if len(coords) >= 4 and coords[0] == coords[-1]:
                    polygons.append([coords])
            if polygons:
                geometry = {"type": "MultiPolygon", "coordinates": polygons}

        if geometry:
            features.append({"type": "Feature", "properties": props, "geometry": geometry})

    return {"type": "FeatureCollection", "features": features}


def _run_overpass(query: str, label: str) -> Dict[str, Any]:
    """Run one Overpass query across the mirrors. Never raises, never invents data."""
    for mirror in OVERPASS_MIRRORS:
        for attempt in range(2):
            try:
                response = requests.post(
                    mirror,
                    data={"data": query},
                    headers=OVERPASS_HEADERS,
                    timeout=60,
                )
                response.raise_for_status()
                result = overpass_to_geojson(response.json())
                if result.get("features"):
                    print(f"Overpass OK via {mirror}: {len(result['features'])} {label}.")
                    result["source"] = "openstreetmap"
                    return result
                break  # valid response, genuinely nothing there — don't retry
            except (requests.RequestException, ValueError) as e:
                print(f"Overpass error on {mirror} for {label} (attempt {attempt + 1}): {e}")
                time.sleep(1.5)

    print(f"Overpass unreachable for {label}; returning an empty collection.")
    return dict(EMPTY)


def fetch_restricted_zones() -> Dict[str, Any]:
    """Real no-drill areas only: military land, cemeteries, airport airside."""
    return _run_overpass(RESTRICTED_QUERY, "restricted zones")


def fetch_protected_areas() -> Dict[str, Any]:
    """National parks and nature reserves — permit required, not prohibited."""
    return _run_overpass(PROTECTED_QUERY, "protected areas")


def fetch_rivers() -> Dict[str, Any]:
    """Rivers and streams from OSM."""
    return _run_overpass(RIVERS_QUERY, "rivers")
