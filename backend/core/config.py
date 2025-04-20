# backend/core/config.py

import os
from pydantic_settings import BaseSettings
from pydantic import AnyHttpUrl, Field # Use Field for default values and descriptions
from typing import List, Optional

# Load environment variables from .env file if it exists
# Note: In a typical setup, the .env file is loaded higher up,
# often when the application starts (e.g., in main.py or via uvicorn).
# pydantic-settings handles .env loading automatically if python-dotenv is installed.
# Ensure python-dotenv is listed in requirements.txt

class Settings(BaseSettings):
    """
    Application settings managed by Pydantic BaseSettings.
    Reads environment variables and provides type validation.
    """
    PROJECT_NAME: str = "AI Tutor Experiment"
    API_V1_STR: str = "/api/v1"

    # Database settings
    # Example: DATABASE_URL=sqlite+aiosqlite:///./data/session.db
    DATABASE_URL: str = Field(default="sqlite+aiosqlite:///./data/session.db", description="Database connection URL for SQLite with async driver")

    # Security settings (Important: Use environment variables for secrets!)
    # Generate a strong secret key (e.g., using `openssl rand -hex 32`)
    # and store it in the .env file
    SECRET_KEY: str = Field(..., description="Secret key for JWT token generation") # (...) means required
    ALGORITHM: str = Field(default="HS256", description="Algorithm used for JWT signing")
    ACCESS_TOKEN_EXPIRE_MINUTES: int = Field(default=60 * 24 * 8, description="Access token expiry time in minutes (e.g., 8 days)") # Example: 8 days

    # LLM API Keys (Important: Load from environment variables, DO NOT hardcode)
    GROQ_API_KEY: Optional[str] = Field(default=None, description="API Key for Groq (LLaMA)")
    GOOGLE_API_KEY: Optional[str] = Field(default=None, description="API Key for Google AI (Gemini)")

    # CORS settings (Cross-Origin Resource Sharing)
    # Define allowed origins for frontend communication. Use environment variables for flexibility.
    # Example env var: BACKEND_CORS_ORIGINS='["http://localhost:8080", "http://127.0.0.1:8080"]' # JSON formatted list
    BACKEND_CORS_ORIGINS: List[AnyHttpUrl] = Field(default=[], description="List of allowed CORS origins")

    # PDF.js worker source path (relative to frontend static serving)
    # This might be needed if the backend serves the frontend files
    PDF_WORKER_SRC: str = Field(default="/static/js/libs/pdfjs/build/pdf.worker.mjs", description="Path to PDF.js worker file")

    class Config:
        # Specify the .env file name if different from default '.env'
        env_file = ".env"
        # Make the variable names case-insensitive when reading from env
        case_sensitive = False
        # Allows extra fields in the environment that are not defined in the model
        extra = 'ignore'

# Create a single instance of the settings to be imported elsewhere
settings = Settings()


# --- ADD THIS DEBUG PRINT ---
print("-" * 20)
print(f"DEBUG [config.py]: Loaded GOOGLE_API_KEY: "
      f"'{settings.GOOGLE_API_KEY[:5]}...{settings.GOOGLE_API_KEY[-5:]}'"
      if settings.GOOGLE_API_KEY else "DEBUG [config.py]: GOOGLE_API_KEY is None or Empty")
print(f"DEBUG [config.py]: Loaded GROQ_API_KEY: "
      f"'{settings.GROQ_API_KEY[:5]}...{settings.GROQ_API_KEY[-5:]}'"
      if settings.GROQ_API_KEY else "DEBUG [config.py]: GROQ_API_KEY is None or Empty")
print("-" * 20)
# --- END DEBUG PRINT ---
# Example of how to access settings in other files:
# from backend.core.config import settings
# db_url = settings.DATABASE_URL