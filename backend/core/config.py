# backend/core/config.py
# Updated with RAG_TOP_K setting

import os
import logging # Added import
import json # Added import for CORS parsing
from typing import List, Optional, Union, Any

from pydantic import AnyHttpUrl, field_validator, ValidationInfo
from pydantic_settings import BaseSettings, SettingsConfigDict

# --- Setup Logger ---
logger = logging.getLogger(__name__)
# Configure logging if needed (e.g., basicConfig)
# logging.basicConfig(level=logging.INFO)


class Settings(BaseSettings):
    """
    Application settings loaded from environment variables or .env file.
    """
    # Core settings
    API_V1_STR: str = "/api/v1"
    PROJECT_NAME: str = "AI Research Tutor Experiment"

    # Database URL (ensure this matches your setup)
    SQLITE_ASYNC_URL: str = "sqlite+aiosqlite:///./data/session.db" # Default if not set in .env
    # DATABASE_URL will automatically use SQLITE_ASYNC_URL if DATABASE_URL itself isn't in .env
    DATABASE_URL: str = SQLITE_ASYNC_URL

    # Security settings
    SECRET_KEY: str = "change_this_super_secret_key_in_production" # Set in .env!
    ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 60 * 24 * 30 # 30 days example

    # API Keys (loaded from .env)
    GROQ_API_KEY: Optional[str] = None
    GOOGLE_API_KEY: Optional[str] = None

    # CORS Origins (loaded from .env)
    # Default allows only the app itself when served from the same origin
    BACKEND_CORS_ORIGINS: List[Union[str, AnyHttpUrl]] = ["http://localhost:8000", "http://127.0.0.1:8000"] # Example default

    # --- RAG SETTINGS ---
    EMBEDDING_MODEL_NAME: str = "sentence-transformers/all-MiniLM-L6-v2" # Example embedding model
    VECTOR_STORE_BASE_PATH: str = "./data/vector_stores" # Directory to save vector stores
    RAG_TOP_K: int = 3 # Number of relevant chunks to retrieve
    # --- END RAG SETTINGS ---

    # Validator for CORS origins (parses string list from .env)
    @field_validator("BACKEND_CORS_ORIGINS", mode='before')
    @classmethod
    def assemble_cors_origins(cls, v: Union[str, List[str]]) -> Union[List[str], str]:
        if isinstance(v, str) and v.startswith("[") and v.endswith("]"):
            # Handles JSON-formatted list like '["http://a.com", "http://b.com"]'
            try:
                return json.loads(v)
            except json.JSONDecodeError:
                logger.warning(f"Could not JSON decode BACKEND_CORS_ORIGINS: {v}. Using empty list.")
                return [] # Return empty list on parse error
        if isinstance(v, str) and not v.startswith("["):
            # Handle comma-separated string like "http://a.com, http://b.com"
            return [i.strip() for i in v.split(",") if i.strip()]
        elif isinstance(v, list):
            # Already a list
            return v
        # Fallback for unexpected types or empty strings
        logger.warning(f"Could not parse BACKEND_CORS_ORIGINS: {v}. Using empty list.")
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
        case_sensitive=True, # Environment variables are case-sensitive
        extra='ignore' # Ignore extra fields from environment
    )

# Create a single settings instance for the application
settings = Settings()

# Optional: Final debug print of critical settings after loading
# Use logger for better practice than print
logger.debug(f"[config.py FINAL]: PROJECT_NAME='{settings.PROJECT_NAME}'")
logger.debug(f"[config.py FINAL]: DATABASE_URL='{settings.DATABASE_URL}'")
logger.debug(f"[config.py FINAL]: ALGORITHM='{settings.ALGORITHM}'")
logger.debug(f"[config.py FINAL]: GOOGLE_API_KEY provided: {'Yes' if settings.GOOGLE_API_KEY else 'No'}")
logger.debug(f"[config.py FINAL]: GROQ_API_KEY provided: {'Yes' if settings.GROQ_API_KEY else 'No'}")
logger.debug(f"[config.py FINAL]: EMBEDDING_MODEL_NAME='{settings.EMBEDDING_MODEL_NAME}'")
logger.debug(f"[config.py FINAL]: VECTOR_STORE_BASE_PATH='{settings.VECTOR_STORE_BASE_PATH}'")
logger.debug(f"[config.py FINAL]: RAG_TOP_K='{settings.RAG_TOP_K}'") # Added debug log for RAG_TOP_K
logger.debug(f"[config.py FINAL]: BACKEND_CORS_ORIGINS={settings.BACKEND_CORS_ORIGINS}")