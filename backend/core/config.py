# backend/core/config.py
# Added ALGORITHM and ACCESS_TOKEN_EXPIRE_MINUTES settings

import os
from typing import List, Optional, Union, Any

from pydantic import AnyHttpUrl, field_validator, ValidationInfo
from pydantic_settings import BaseSettings, SettingsConfigDict

class Settings(BaseSettings):
    """
    Application settings loaded from environment variables or .env file.
    """
    # Core settings
    API_V1_STR: str = "/api/v1"
    PROJECT_NAME: str = "AI Tutor Experiment"

    # Database URL (ensure this matches your setup)
    SQLITE_ASYNC_URL: str = "sqlite+aiosqlite:///./data/session.db"
    DATABASE_URL: str = SQLITE_ASYNC_URL

    # Security settings
    SECRET_KEY: str = "change_this_super_secret_key_in_production" # Set in .env!
    # --- ADDED ALGORITHM AND EXPIRY ---
    # Algorithm for encoding JWT tokens (HS256 is common)
    ALGORITHM: str = "HS256"
    # Default access token expiration time in minutes (e.g., 30 days)
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 60 * 24 * 30
    # --- END ADDED ---

    # API Keys (loaded from .env)
    GROQ_API_KEY: Optional[str] = None
    GOOGLE_API_KEY: Optional[str] = None

    # CORS Origins (loaded from .env)
    # Default allows only the app itself when served from the same origin
    BACKEND_CORS_ORIGINS: List[Union[str, AnyHttpUrl]] = []

    # Validator for CORS origins (parses string list from .env)
    @field_validator("BACKEND_CORS_ORIGINS", mode='before')
    @classmethod
    def assemble_cors_origins(cls, v: Union[str, List[str]]) -> Union[List[str], str]:
        if isinstance(v, str) and v.startswith("[") and v.endswith("]"):
            import json
            try:
                return json.loads(v)
            except json.JSONDecodeError:
                pass
        if isinstance(v, str) and not v.startswith("["):
            return [i.strip() for i in v.split(",") if i.strip()]
        elif isinstance(v, list):
            return v
        print(f"Warning: Could not parse BACKEND_CORS_ORIGINS: {v}. Using empty list.")
        return []

    # Validator for API Keys (strips quotes/whitespace)
    @field_validator('GOOGLE_API_KEY', 'GROQ_API_KEY', mode='before')
    @classmethod
    def strip_quotes_and_spaces(cls, v: Optional[str]) -> Optional[str]:
        """Remove leading/trailing whitespace and quotes from API keys."""
        if isinstance(v, str):
            return v.strip().strip('"\'')
        return v

    # Pydantic settings configuration
    model_config = SettingsConfigDict(
        env_file='.env',
        env_file_encoding='utf-8',
        case_sensitive=True,
        extra='ignore'
    )

# Create a single settings instance for the application
settings = Settings()

# Optional: Final debug print if needed
print(f"DEBUG [config.py FINAL]: ALGORITHM='{settings.ALGORITHM}'")
print(f"DEBUG [config.py FINAL]: GOOGLE_API_KEY='{settings.GOOGLE_API_KEY}'")

