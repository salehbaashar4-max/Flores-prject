from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from app.config import settings
from app.routers import gee, osm, geodata, ai, wms
from app.services.gee_service import initialize_gee

app = FastAPI(title="Flores Groundwater API")

# Setup CORS
origins = settings.cors_origins
if "http://localhost:5173" not in origins:
    origins.append("http://localhost:5173")

app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

@app.on_event("startup")
async def startup_event():
    if settings.gee_service_account and settings.gee_key_file and settings.gee_project_id:
        initialize_gee(
            settings.gee_service_account,
            settings.gee_key_file,
            settings.gee_project_id
        )
    else:
        print("GEE configuration incomplete. Earth Engine will not be initialized.")
    
    if settings.chatanywhere_api_key:
        print(f"chatanywhere configured (model: {settings.chatanywhere_model}). AI analysis is available.")
    elif settings.gemini_api_key:
        print(f"Gemini configured (model: {settings.gemini_model}). AI analysis is available.")
    elif settings.openrouter_api_key:
        print(f"OpenRouter configured (model: {settings.openrouter_model}). AI analysis is available.")
    elif settings.anthropic_api_key:
        print("Anthropic API key configured. AI analysis is available.")
    else:
        print("No AI provider key set. AI analysis will use the expert fallback templates.")

app.include_router(gee.router, prefix="/api/gee", tags=["Google Earth Engine"])
app.include_router(osm.router, prefix="/api/osm", tags=["OpenStreetMap"])
app.include_router(geodata.router, prefix="/api/geodata", tags=["Geodata"])
app.include_router(ai.router, prefix="/api/ai", tags=["AI Analysis"])
app.include_router(wms.router, prefix="/api/wms", tags=["WMS Proxy"])

@app.get("/api/health")
def health_check():
    return {"status": "healthy", "ai_available": settings.ai_available}
