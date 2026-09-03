from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from typing import Optional, Dict, Any, List
from app.config import settings
from app.services import ai_service

router = APIRouter()


class LocationAnalysisRequest(BaseModel):
    latitude: float
    longitude: float
    context_data: Optional[Dict[str, Any]] = None
    language: Optional[str] = None


class ChatRequest(BaseModel):
    message: str
    conversation_history: Optional[List[Dict[str, str]]] = None
    language: Optional[str] = None


class ReportRequest(BaseModel):
    area_data: Dict[str, Any]
    language: Optional[str] = None


@router.post("/analyze-location")
async def analyze_location(request: LocationAnalysisRequest):
    """Analyze a specific location for groundwater potential using AI."""
    try:
        result = ai_service.analyze_location(
            settings.anthropic_api_key,
            request.latitude,
            request.longitude,
            request.context_data,
            request.language,
        )
        return {"analysis": result}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"AI analysis failed: {str(e)}")


@router.post("/chat")
async def chat(request: ChatRequest):
    """Chat with AI assistant about groundwater analysis."""
    try:
        result = ai_service.chat_analysis(
            settings.anthropic_api_key,
            request.message,
            request.conversation_history,
            request.language,
        )
        return {"response": result}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"AI chat failed: {str(e)}")


@router.post("/generate-report")
async def generate_report(request: ReportRequest):
    """Generate a comprehensive groundwater assessment report."""
    try:
        result = ai_service.generate_report(
            settings.anthropic_api_key,
            request.area_data,
            request.language,
        )
        return {"report": result}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Report generation failed: {str(e)}")
