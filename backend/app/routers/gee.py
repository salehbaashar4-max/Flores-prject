from fastapi import APIRouter, HTTPException
from app.services.gee_service import (
    get_elevation_tiles, 
    get_ndvi_tiles, 
    get_moisture_tiles, 
    get_groundwater_potential
)

router = APIRouter()

@router.get("/elevation")
def elevation():
    try:
        return get_elevation_tiles()
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/ndvi")
def ndvi():
    try:
        return get_ndvi_tiles()
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/moisture")
def moisture():
    try:
        return get_moisture_tiles()
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/potential")
def potential():
    try:
        return get_groundwater_potential()
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
