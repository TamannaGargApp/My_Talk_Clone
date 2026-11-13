from functools import lru_cache
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")
    environment: str = "development"
    frontend_url: str = "http://localhost:5500"
    cors_origins: str = "http://localhost:5500,http://127.0.0.1:5500"
    mongodb_uri: str = ""
    mongodb_database: str = "voice_agent"
    gemini_api_key: str = ""
    gemini_model: str = "gemini-3.5-flash-lite"
    jwt_secret: str = ""
    jwt_expire_minutes: int = 1440
    google_client_id: str = ""
    google_client_secret: str = ""
    google_redirect_uri: str = "http://localhost:8000/api/auth/google/callback"


@lru_cache
def get_settings() -> Settings:
    return Settings()
