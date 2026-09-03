"""
WMS proxy + capability discovery for Indonesian geological / hydrogeological servers.

Solves the browser CORS block by fetching WMS tiles server-side and streaming them
back to the frontend. Also parses each server's GetCapabilities document at runtime so
the real layer names never need to be hard-coded — they are discovered live.

Sources (base URLs provided by the project owner):
  - ESDM  : national geology + groundwater basins (Cekungan Air Tanah / CAT)
  - BIG   : Ina-Geoportal (Badan Informasi Geospasial)
  - OneGeology : global geology fallback

Layer names for each source can be overridden via environment variables:
  WMS_ESDM_GEOLOGY_LAYER, WMS_ESDM_GROUNDWATER_LAYER, WMS_BIG_LAYER, WMS_ONEGEOLOGY_LAYER
Otherwise they are auto-detected from GetCapabilities using keyword matching.
"""
import os
import time
import base64
import xml.etree.ElementTree as ET
from typing import Dict, Any, List, Optional

import requests

HEADERS = {
    "User-Agent": "FloresGroundwaterDashboard/1.0 (hydrogeology research; contact: admin@flores.local)",
}
TIMEOUT = 30

# 1x1 transparent PNG — returned instead of a broken tile when an upstream fails.
_TRANSPARENT_PNG = base64.b64decode(
    "iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAQAAAC1HAwCAAAAC0lEQVR42mNkYPhfDwAChwGA60e6kgAAAABJRU5ErkJggg=="
)

# name -> {base url, human title, keyword hints for auto layer detection}
# Primary sources are now stable GLOBAL servers (USGS geology, BGR WHYMAP groundwater);
# the Indonesian government servers are kept as optional fallbacks.
WMS_SOURCES: Dict[str, Dict[str, Any]] = {
    # --- Global, stable ---
    "usgs": {
        "base": "https://mrdata.usgs.gov/services/gscworld",
        "title": "USGS - World Geology (GSC)",
        "geology_keywords": ["geology", "geolog", "gsc_worldgeology", "bedrock", "litholog"],
        "groundwater_keywords": [],  # USGS gscworld is geology only
    },
    "bgr": {
        "base": "https://services.bgr.de/wms/grundwasser/whymap/",
        "title": "BGR WHYMAP - World Groundwater Resources",
        "geology_keywords": [],
        "groundwater_keywords": ["whymap", "groundwater", "grundwasser", "aquifer", "recharge", "resources"],
    },
    # --- Indonesian government (optional fallbacks; may require domestic network) ---
    "esdm": {
        "base": "https://geoportal.esdm.go.id/server/services/Geologi/MapServer/WMSServer",
        "title": "ESDM - Geologi & Air Tanah (Indonesia)",
        "geology_keywords": ["geolog", "litolog", "batuan", "formasi"],
        "groundwater_keywords": ["air_tanah", "air tanah", "cat", "cekungan", "hidrogeolog", "akuifer"],
    },
    "big": {
        "base": "https://palapa.big.go.id/geoserver/wms",
        "title": "BIG - Ina-Geoportal (Indonesia)",
        "geology_keywords": ["geolog", "litolog", "batuan"],
        "groundwater_keywords": ["air_tanah", "air tanah", "cat", "cekungan", "hidrogeolog", "sungai", "das"],
    },
    "onegeology": {
        "base": "http://maps.onegeology.org/Geoserver/wms",
        "title": "OneGeology - Global geology (fallback)",
        "geology_keywords": ["geolog", "bedrock", "litholog", "idn", "indonesia"],
        "groundwater_keywords": ["aquifer", "hydrogeolog", "groundwater"],
    },
}

# Simple in-memory cache for discovery (capabilities parsing is slow / rate-limited upstream).
_CACHE: Dict[str, Any] = {}
_CACHE_TTL = 600  # seconds


def _localname(tag: str) -> str:
    """Strip the XML namespace from a tag, e.g. '{ns}Layer' -> 'Layer'."""
    return tag.split("}")[-1]


def parse_layers(xml_bytes: bytes) -> List[Dict[str, str]]:
    """Parse a WMS GetCapabilities document into a flat list of {name, title} layers.

    Only layers that carry a <Name> (i.e. are actually requestable) are returned.
    Namespace-agnostic so it works across WMS 1.1.1 and 1.3.0 servers.
    """
    layers: List[Dict[str, str]] = []
    root = ET.fromstring(xml_bytes)
    for el in root.iter():
        if _localname(el.tag) != "Layer":
            continue
        name_el = next((c for c in el if _localname(c.tag) == "Name"), None)
        title_el = next((c for c in el if _localname(c.tag) == "Title"), None)
        if name_el is not None and (name_el.text or "").strip():
            layers.append({
                "name": name_el.text.strip(),
                "title": (title_el.text or "").strip() if title_el is not None else "",
            })
    return layers


def fetch_layers(source: str) -> List[Dict[str, str]]:
    """Fetch + parse GetCapabilities for a source. Raises on network/parse failure."""
    cfg = WMS_SOURCES[source]
    resp = requests.get(
        cfg["base"],
        params={"service": "WMS", "version": "1.3.0", "request": "GetCapabilities"},
        headers=HEADERS,
        timeout=TIMEOUT,
    )
    resp.raise_for_status()
    return parse_layers(resp.content)


def _pick_layer(layers: List[Dict[str, str]], keywords: List[str]) -> Optional[str]:
    """Return the first layer whose name/title contains any keyword (case-insensitive)."""
    for lyr in layers:
        hay = (lyr["name"] + " " + lyr["title"]).lower()
        if any(k.lower() in hay for k in keywords):
            return lyr["name"]
    return None


def discover(force: bool = False) -> Dict[str, Any]:
    """Probe every source's GetCapabilities and resolve a geology + groundwater layer each.

    Env-var overrides win over auto-detection. Result is cached for _CACHE_TTL seconds so
    the frontend can poll cheaply. Unreachable sources are reported as reachable=False
    rather than raising, so the UI degrades gracefully.
    """
    now = time.time()
    if not force and _CACHE.get("ts") and (now - _CACHE["ts"] < _CACHE_TTL):
        return _CACHE["data"]

    env = {
        "usgs": os.getenv("WMS_USGS_LAYER", ""),
        "bgr": os.getenv("WMS_BGR_LAYER", ""),
        "esdm_geology": os.getenv("WMS_ESDM_GEOLOGY_LAYER", ""),
        "esdm_groundwater": os.getenv("WMS_ESDM_GROUNDWATER_LAYER", ""),
        "big": os.getenv("WMS_BIG_LAYER", ""),
        "onegeology": os.getenv("WMS_ONEGEOLOGY_LAYER", ""),
    }

    result: Dict[str, Any] = {}
    for source, cfg in WMS_SOURCES.items():
        entry: Dict[str, Any] = {
            "title": cfg["title"],
            "reachable": False,
            "layer_count": 0,
            "geology_layer": None,
            "groundwater_layer": None,
            "error": None,
        }
        try:
            layers = fetch_layers(source)
            entry["reachable"] = True
            entry["layer_count"] = len(layers)
            entry["geology_layer"] = _pick_layer(layers, cfg["geology_keywords"])
            entry["groundwater_layer"] = _pick_layer(layers, cfg["groundwater_keywords"])
        except Exception as e:  # noqa: BLE001 — report, never crash discovery
            entry["error"] = str(e)[:200]

        # Env overrides take precedence when provided.
        if source == "usgs":
            entry["geology_layer"] = env["usgs"] or entry["geology_layer"]
        elif source == "bgr":
            entry["groundwater_layer"] = env["bgr"] or entry["groundwater_layer"]
        elif source == "esdm":
            entry["geology_layer"] = env["esdm_geology"] or entry["geology_layer"]
            entry["groundwater_layer"] = env["esdm_groundwater"] or entry["groundwater_layer"]
        elif source == "big":
            entry["groundwater_layer"] = env["big"] or entry["groundwater_layer"]
        elif source == "onegeology":
            entry["geology_layer"] = env["onegeology"] or entry["geology_layer"]

        result[source] = entry

    _CACHE["ts"] = now
    _CACHE["data"] = result
    return result


def proxy(source: str, params: Dict[str, str]):
    """Forward a WMS request (GetMap / GetCapabilities) to the upstream server.

    Returns (content_bytes, status_code, content_type). For GetMap requests, any
    failure (network error, non-200 status, or a non-image error page) is turned into
    a transparent PNG so map tiles never render as broken images.
    """
    cfg = WMS_SOURCES[source]
    request_type = (params.get("request") or params.get("REQUEST") or "").lower()
    is_getmap = request_type == "getmap"
    try:
        resp = requests.get(cfg["base"], params=params, headers=HEADERS, timeout=TIMEOUT)
        ctype = resp.headers.get("Content-Type", "application/octet-stream")
        if is_getmap and (resp.status_code != 200 or "image" not in ctype.lower()):
            return _TRANSPARENT_PNG, 200, "image/png"
        return resp.content, resp.status_code, ctype
    except Exception:  # noqa: BLE001
        if is_getmap:
            return _TRANSPARENT_PNG, 200, "image/png"
        return b"WMS upstream unreachable", 502, "text/plain"


def transparent_tile():
    return _TRANSPARENT_PNG
