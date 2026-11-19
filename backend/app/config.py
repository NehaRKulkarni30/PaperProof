import os
from functools import lru_cache
from typing import List
from pydantic_settings import BaseSettings, SettingsConfigDict


_BACKEND_DIR = os.path.dirname(os.path.dirname(__file__))
_ROOT_DIR = os.path.dirname(_BACKEND_DIR)


class Settings(BaseSettings):
    gemini_api_key: str = ""
    gemini_model: str = "gemini-3.5-flash-lite"
    jwt_secret: str = "paperproof-dev-secret-change-in-prod"
    jwt_algorithm: str = "HS256"
    jwt_expire_minutes: int = 60 * 24 * 7  # 7 days
    google_client_id: str = ""
    contact_email: str = "ai-innovators@paperproof.app"
    database_url: str = "sqlite:///./paperproof.db"
    cors_origins: str = "http://localhost:5173,http://127.0.0.1:5173"
    max_upload_bytes: int = 15 * 1024 * 1024  # 15 MB

    model_config = SettingsConfigDict(
        env_file=(os.path.join(_ROOT_DIR, ".env"), os.path.join(_BACKEND_DIR, ".env")),
        env_file_encoding="utf-8",
        extra="ignore",
    )

    @property
    def cors_origin_list(self) -> List[str]:
        return [o.strip() for o in self.cors_origins.split(",") if o.strip()]


@lru_cache()
def get_settings() -> Settings:
    return Settings()
