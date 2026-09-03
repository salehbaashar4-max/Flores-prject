from fastapi import APIRouter
from app.services.geodata_service import get_cat_basins, get_geology, get_rivers

router = APIRouter()

@router.get("/cat-basins")
def cat_basins():
    """Returns official Cekungan Air Tanah (CAT) basins as GeoJSON."""
    return get_cat_basins()

@router.get("/geology")
def geology():
    """Returns geology & lithology formations as GeoJSON."""
    return get_geology()

@router.get("/rivers")
def rivers():
    """Returns rivers network as GeoJSON."""
    return get_rivers()
