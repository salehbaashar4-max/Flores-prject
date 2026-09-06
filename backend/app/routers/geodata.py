from fastapi import APIRouter

from app.services.geodata_service import get_rivers

router = APIRouter()


@router.get("/rivers")
def rivers():
    """Real river and stream network from OpenStreetMap."""
    return get_rivers()
