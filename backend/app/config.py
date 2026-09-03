from pydantic_settings import BaseSettings
from typing import List

class Settings(BaseSettings):
    gee_service_account: str = ""
    gee_key_file: str = ""
    gee_project_id: str = ""
    allowed_origins: str = "http://localhost:5173"
    anthropic_api_key: str = ""
    gemini_api_key: str = ""
    gemini_model: str = "gemini-2.0-flash"
    openrouter_api_key: str = ""
    openrouter_model: str = "google/gemini-2.0-flash-001"
    # chatanywhere free OpenAI-compatible gateway (https://github.com/chatanywhere/GPT_API_free)
    chatanywhere_api_key: str = ""
    chatanywhere_base_url: str = "https://api.chatanywhere.tech/v1"
    chatanywhere_model: str = "gpt-4o-mini"

    @property
    def cors_origins(self) -> List[str]:
        return [origin.strip() for origin in self.allowed_origins.split(",") if origin.strip()]

    @property
    def ai_available(self) -> bool:
        """True when at least one working AI provider key is configured."""
        return bool(
            self.chatanywhere_api_key
            or self.gemini_api_key
            or self.openrouter_api_key
            or self.anthropic_api_key
        )

    class Config:
        env_file = ".env"

settings = Settings()
