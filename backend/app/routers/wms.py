"""WMS proxy endpoints — bypass browser CORS for Indonesian geo/hydro map servers."""
from fastapi import APIRouter, Request, HTTPException, Response

from app.services import wms_service

router = APIRouter()


@router.get("/sources")
def list_sources():
    """Static list of configured WMS sources and their base URLs."""
    return {
        name: {"title": cfg["title"], "base": cfg["base"]}
        for name, cfg in wms_service.WMS_SOURCES.items()
    }


@router.get("/config")
def wms_config(force: bool = False):
    """Live discovery: for each source report reachability and the resolved
    geology / groundwater layer names (auto-detected from GetCapabilities or env override).
    The frontend calls this to know which real WMS layers it can switch on."""
    return wms_service.discover(force=force)


@router.get("/{source}/layers")
def source_layers(source: str):
    """Full list of requestable layers for a source (for manual inspection/tuning)."""
    if source not in wms_service.WMS_SOURCES:
        raise HTTPException(status_code=404, detail=f"Unknown WMS source '{source}'")
    try:
        return {"source": source, "layers": wms_service.fetch_layers(source)}
    except Exception as e:  # noqa: BLE001
        raise HTTPException(status_code=502, detail=f"GetCapabilities failed: {e}")


@router.get("/{source}")
def wms_proxy(source: str, request: Request):
    """Generic WMS passthrough (GetMap / GetCapabilities). Forwards the query string
    to the upstream server so the browser never hits it directly (CORS bypass)."""
    if source not in wms_service.WMS_SOURCES:
        raise HTTPException(status_code=404, detail=f"Unknown WMS source '{source}'")
    params = dict(request.query_params)
    content, status, ctype = wms_service.proxy(source, params)
    return Response(content=content, status_code=status, media_type=ctype)
