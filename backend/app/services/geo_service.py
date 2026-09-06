"""Place search and point-level ground truth for the Flores region.

Search runs two sources at once and merges them:

  * Photon (Komoot's OSM geocoder) — built for free text, so it tolerates
    typos, partial names and points of interest: mosques, schools, hamlets,
    individual named buildings, not only village and town names.
  * Overpass — an exact name sweep of the project's own bounding box, which
    catches local features Photon's global index ranks poorly or misses.

Results inside the region are ranked first, then by how much of the query the
name actually accounts for. Nothing is fabricated: no match returns an empty
list, and the caller is expected to say so.

site_facts() is the other half: given a coordinate it returns only measured
values — bedrock unit, elevation, slope, rainfall, nearby no-drill features —
so the assistant can answer from data instead of guessing.
"""
import re
from concurrent.futures import ThreadPoolExecutor
from typing import Any, Dict, List, Optional

import requests

# Flores + Komodo/Rinca, Lembata, Adonara, Solor and the small islands between.
MIN_LAT, MIN_LON, MAX_LAT, MAX_LON = -9.30, 119.00, -7.80, 124.30

HEADERS = {
    "User-Agent": "FloresGroundwaterDashboard/1.0 (hydrogeology research; contact: admin@flores.local)",
    "Accept": "application/json",
}

PHOTON_URL = "https://photon.komoot.io/api/"
OVERPASS_MIRRORS = [
    "https://overpass-api.de/api/interpreter",
    "https://overpass.kumi.systems/api/interpreter",
]
MACROSTRAT_URL = "https://macrostrat.org/api/v2/geologic_units/map"

# Words that describe a category rather than identify a place. They still help
# inside a multi-word phrase, but on their own they would match half the island.
GENERIC = {
    "masjid", "mesjid", "mushola", "gereja", "kapela", "sekolah", "sd", "smp", "sma",
    "desa", "dusun", "kampung", "kelurahan", "kecamatan", "kabupaten", "kota",
    "pulau", "gunung", "sungai", "kali", "jalan", "jln", "raya", "pasar", "puskesmas",
    "the", "of", "di", "in", "at",
}


def _tokens(q: str) -> List[str]:
    return [t for t in re.split(r"[\s,./|-]+", q.strip().lower()) if t]


def _in_region(lat: float, lon: float) -> bool:
    return MIN_LAT <= lat <= MAX_LAT and MIN_LON <= lon <= MAX_LON


# ----------------------------------------------------------------------------
# sources
# ----------------------------------------------------------------------------

def _photon(q: str, limit: int) -> List[Dict[str, Any]]:
    """Free-text geocoding, biased toward the region but not fenced into it."""
    try:
        resp = requests.get(
            PHOTON_URL,
            params={"q": q, "limit": limit, "lat": -8.6, "lon": 121.4, "lang": "en"},
            headers=HEADERS,
            timeout=12,
        )
        resp.raise_for_status()
        features = resp.json().get("features", [])
    except Exception as e:  # noqa: BLE001
        print(f"Photon search failed: {e}")
        return []

    out: List[Dict[str, Any]] = []
    for f in features:
        coords = (f.get("geometry") or {}).get("coordinates") or []
        if len(coords) != 2:
            continue
        p = f.get("properties", {})
        lon, lat = float(coords[0]), float(coords[1])
        label = ", ".join(
            x for x in (p.get("district"), p.get("city"), p.get("county"),
                        p.get("state"), p.get("country")) if x
        )
        out.append({
            "name": p.get("name") or label or "?",
            "label": label,
            "lat": lat,
            "lon": lon,
            "category": p.get("osm_value") or p.get("osm_key") or "place",
            "source": "photon",
            "in_region": _in_region(lat, lon),
        })
    return out


def _name_regex(tokens: List[str]) -> str:
    """Build one Overpass alternation from the query's word groups.

    Longer phrases come first so 'Masjid Baitul Makmur' outranks a lone
    'Makmur'. Capped so the regex stays cheap for the server to run.
    """
    grams: List[str] = []
    n = len(tokens)
    for size in range(min(n, 4), 1, -1):
        for i in range(0, n - size + 1):
            grams.append(r"\s+".join(re.escape(t) for t in tokens[i:i + size]))
    for t in tokens:
        if len(t) >= 5 and t not in GENERIC:
            grams.append(re.escape(t))
    seen, uniq = set(), []
    for g in grams:
        if g not in seen:
            seen.add(g)
            uniq.append(g)
    return "|".join(uniq[:14])


def _overpass_names(q: str, limit: int) -> List[Dict[str, Any]]:
    """Exact name sweep of the region — this is what finds the local mosque."""
    tokens = _tokens(q)
    if not tokens:
        return []
    pattern = _name_regex(tokens)
    if not pattern:
        return []

    query = (
        f'[out:json][timeout:25];'
        f'nwr["name"~"{pattern}",i]'
        f'({MIN_LAT},{MIN_LON},{MAX_LAT},{MAX_LON});'
        f'out center {max(limit * 3, 30)};'
    )

    elements = []
    for mirror in OVERPASS_MIRRORS:
        try:
            resp = requests.post(mirror, data={"data": query}, headers=HEADERS, timeout=30)
            resp.raise_for_status()
            elements = resp.json().get("elements", [])
            break
        except Exception as e:  # noqa: BLE001
            print(f"Overpass name search failed on {mirror}: {e}")

    out: List[Dict[str, Any]] = []
    for el in elements:
        tags = el.get("tags", {})
        name = tags.get("name")
        if not name:
            continue
        if el.get("type") == "node":
            lat, lon = el.get("lat"), el.get("lon")
        else:
            center = el.get("center") or {}
            lat, lon = center.get("lat"), center.get("lon")
        if lat is None or lon is None:
            continue
        label = ", ".join(
            x for x in (tags.get("addr:village"), tags.get("addr:subdistrict"),
                        tags.get("addr:city"), tags.get("addr:county"),
                        tags.get("addr:state")) if x
        )
        out.append({
            "name": name,
            "label": label or "Flores & sekitarnya",
            "lat": float(lat),
            "lon": float(lon),
            "category": (tags.get("amenity") or tags.get("place") or tags.get("shop")
                         or tags.get("tourism") or tags.get("building") or "place"),
            "source": "overpass",
            "in_region": True,
        })
    return out


# ----------------------------------------------------------------------------
# search
# ----------------------------------------------------------------------------

def _score(item: Dict[str, Any], tokens: List[str], q_lower: str) -> float:
    hay = f"{item['name']} {item.get('label') or ''}".lower()
    score = 0.0
    if q_lower and q_lower in hay:
        score += 8.0
    matched = sum(1 for t in tokens if t in hay)
    score += 2.0 * matched
    if tokens:
        score += 4.0 * (matched / len(tokens))
    if item.get("in_region"):
        score += 10.0
    if item.get("source") == "overpass":
        score += 1.0
    return score


def search_places(q: str, limit: int = 10) -> Dict[str, Any]:
    """Search both sources in parallel and return one ranked list."""
    q = (q or "").strip()
    if len(q) < 2:
        return {"query": q, "results": []}

    with ThreadPoolExecutor(max_workers=2) as pool:
        photon_job = pool.submit(_photon, q, max(limit, 8))
        overpass_job = pool.submit(_overpass_names, q, limit)
        try:
            photon_hits = photon_job.result(timeout=15)
        except Exception:  # noqa: BLE001
            photon_hits = []
        try:
            overpass_hits = overpass_job.result(timeout=32)
        except Exception:  # noqa: BLE001
            overpass_hits = []

    tokens = _tokens(q)
    q_lower = q.lower()
    merged: Dict[str, Dict[str, Any]] = {}
    for item in overpass_hits + photon_hits:
        key = f"{item['name'].lower()}@{round(item['lat'], 3)},{round(item['lon'], 3)}"
        if key in merged:
            continue
        item["score"] = round(_score(item, tokens, q_lower), 2)
        merged[key] = item

    results = sorted(merged.values(), key=lambda r: r["score"], reverse=True)[:limit]
    return {"query": q, "results": results}


def resolve_place(q: str) -> Optional[Dict[str, Any]]:
    """Best single in-region match for a free-text place name, or None."""
    results = search_places(q, limit=6).get("results", [])
    for r in results:
        if r.get("in_region"):
            return r
    return None


# ----------------------------------------------------------------------------
# point facts
# ----------------------------------------------------------------------------

def _macrostrat(lat: float, lon: float) -> Dict[str, Any]:
    resp = requests.get(
        MACROSTRAT_URL,
        params={"lat": lat, "lng": lon},
        headers=HEADERS,
        timeout=12,
    )
    resp.raise_for_status()
    data = (resp.json().get("success") or {}).get("data") or []
    if not data:
        return {}
    u = data[0]
    return {
        "bedrock_unit": u.get("name"),
        "lithology": u.get("lith"),
        "age": u.get("best_int_name") or u.get("b_int_name"),
        "age_range_ma": f"{u.get('t_age')}–{u.get('b_age')}",
        "geology_source": "GSC world bedrock map via Macrostrat (CC-BY 4.0)",
    }


def _nearby_restrictions(lat: float, lon: float, radius_m: int = 1500) -> List[str]:
    query = (
        f'[out:json][timeout:20];'
        f'('
        f'nwr["amenity"="grave_yard"](around:{radius_m},{lat},{lon});'
        f'nwr["landuse"="cemetery"](around:{radius_m},{lat},{lon});'
        f'nwr["landuse"="military"](around:{radius_m},{lat},{lon});'
        f'nwr["aeroway"="aerodrome"](around:{radius_m},{lat},{lon});'
        f');'
        f'out center 10;'
    )
    for mirror in OVERPASS_MIRRORS:
        try:
            resp = requests.post(mirror, data={"data": query}, headers=HEADERS, timeout=25)
            resp.raise_for_status()
            names = []
            for el in resp.json().get("elements", []):
                tags = el.get("tags", {})
                kind = ("pemakaman" if tags.get("amenity") == "grave_yard"
                        or tags.get("landuse") == "cemetery"
                        else "militer" if tags.get("landuse") == "military"
                        else "bandara")
                names.append(f"{tags.get('name') or 'tanpa nama'} ({kind})")
            return names
        except Exception as e:  # noqa: BLE001
            print(f"Nearby restriction lookup failed on {mirror}: {e}")
    return []


def site_facts(lat: float, lon: float) -> Dict[str, Any]:
    """Measured values at one coordinate. Every source is optional and is
    simply left out when it fails — never replaced with a plausible guess."""
    facts: Dict[str, Any] = {
        "latitude": round(lat, 5),
        "longitude": round(lon, 5),
        "in_region": _in_region(lat, lon),
    }

    try:
        facts.update(_macrostrat(lat, lon))
    except Exception as e:  # noqa: BLE001
        print(f"Macrostrat lookup failed: {e}")

    try:
        from app.services.gee_service import point_terrain
        facts.update(point_terrain(lat, lon))
    except Exception as e:  # noqa: BLE001
        print(f"Earth Engine point lookup failed: {e}")

    try:
        nearby = _nearby_restrictions(lat, lon)
        if nearby:
            facts["restricted_within_1500m"] = nearby
    except Exception as e:  # noqa: BLE001
        print(f"Nearby restriction lookup failed: {e}")

    return facts
