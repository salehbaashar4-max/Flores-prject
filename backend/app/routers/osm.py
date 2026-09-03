from fastapi import APIRouter, HTTPException
from app.services.osm_service import fetch_restricted_zones

router = APIRouter()

@router.get("/restricted-zones")
def restricted_zones():
    try:
        return fetch_restricted_zones()
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
