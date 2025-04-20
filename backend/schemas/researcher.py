# backend/schemas/researcher.py

import uuid
from pydantic import BaseModel, EmailStr, Field
from typing import Optional

# Base properties shared by other schemas
class ResearcherBase(BaseModel):
    email: EmailStr = Field(..., description="Researcher's email address (used for login)")
    full_name: Optional[str] = Field(default=None, description="Researcher's full name")

# Properties to receive via API on creation
class ResearcherCreate(ResearcherBase):
    password: str = Field(..., min_length=8, description="Researcher's password (will be hashed)")

# Properties properties received via API on update (optional)
# class ResearcherUpdate(ResearcherBase):
#    password: Optional[str] = Field(default=None, min_length=8, description="Optional new password")
#    is_active: Optional[bool] = None

# Properties to return via API (never includes password hash)
class ResearcherRead(ResearcherBase):
    researcher_id: uuid.UUID
    is_active: bool

    class Config:
        orm_mode = True # Pydantic V1
        # from_attributes = True # Pydantic V2