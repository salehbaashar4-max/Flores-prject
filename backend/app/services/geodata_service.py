"""Vector map data that comes from neither Earth Engine nor a WMS server.

What used to live here — three "CAT basin" rectangles and two lithology
rectangles — was hand-typed bounding boxes, not data, so it is gone:

  * Lithology now comes from the Macrostrat vector tiles the map loads
    directly (Geological Survey of Canada world bedrock map, CC-BY 4.0).
  * The official Indonesian CAT basins (ESDM) have no publicly reachable
    endpoint from this host, so that layer is omitted rather than faked.

Rivers stay, because they were always real OSM geometry.
"""
from typing import Any, Dict

from app.services.osm_service import fetch_rivers as fetch_osm_rivers


def get_rivers() -> Dict[str, Any]:
    """Real river and stream geometry from OpenStreetMap."""
    return fetch_osm_rivers()
