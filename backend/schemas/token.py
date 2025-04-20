# backend/schemas/token.py

from pydantic import BaseModel
from typing import Optional
import uuid

class Token(BaseModel):
    """Schema for the access token response."""
    access_token: str
    token_type: str

class TokenData(BaseModel):
    """Schema for the data embedded within the JWT token."""
    username: Optional[str] = None
    user_id: Optional[uuid.UUID] = None # Assuming user ID is UUID
    # Add other fields like roles if needed
    roles: Optional[list[str]] = None