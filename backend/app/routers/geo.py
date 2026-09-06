"""Place search and point-level ground truth."""
from fastapi import APIRouter, HTTPException, Query

from app.services import geo_service

router = APIRouter()


@router.get("/search")
def search(q: str = Query(..., min_length=1), limit: int = 10):
    """Free-text place search across the region: villages, mosques, schools,
    named buildings — anything OpenStreetMap holds, not just settlements."""
    try:
        return geo_service.search_places(q, limit=min(max(limit, 1), 20))
    except Exception as e:  # noqa: BLE001
        raise HTTPException(status_code=502, detail=f"Place search failed: {e}")


@router.get("/site")
def site(lat: float, lon: float):
    """Measured values at one coordinate: bedrock unit, elevation, slope,
    rainfall, and any no-drill feature within 1.5 km."""
    try:
        return geo_service.site_facts(lat, lon)
    except Exception as e:  # noqa: BLE001
        raise HTTPException(status_code=502, detail=f"Site lookup failed: {e}")
