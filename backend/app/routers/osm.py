from fastapi import APIRouter, HTTPException

from app.services.osm_service import fetch_protected_areas, fetch_restricted_zones

router = APIRouter()


@router.get("/restricted-zones")
def restricted_zones():
    """Areas where drilling is genuinely prohibited: military, cemeteries, airports."""
    try:
        return fetch_restricted_zones()
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/protected-areas")
def protected_areas():
    """National parks and nature reserves — a permit zone, not a drilling ban."""
    try:
        return fetch_protected_areas()
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
