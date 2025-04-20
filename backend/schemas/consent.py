# backend/schemas/consent.py

import uuid
from datetime import datetime
from pydantic import BaseModel, Field, validator
from typing import Dict, Any, Optional, List

from .participant import ParticipantRead # Import the read schema for participant

# Base schema with fields common to Create and Read/Update
class ConsentBase(BaseModel):
    demographics: Optional[Dict[str, Any]] = Field(default=None, description="Demographic data (age, gender, etc.)") # Phase 1 [cite: 9]
    baseline_data: Optional[Dict[str, Any]] = Field(default=None, description="Baseline data (LLM experience, topic familiarity)") # Phase 1 [cite: 10, 11]

# Schema for data required when creating a new consent/session record
class ConsentCreate(ConsentBase):
    # participant_uuid will be generated or assigned by the backend service logic
    # session_uuid, assigned_app, assigned_paper, timestamps are also handled by backend
    pass # Inherits fields from ConsentBase

# Schema for updating consent/session details (e.g., marking consent given)
class ConsentUpdate(BaseModel):
    consent_timestamp: Optional[datetime] = None
    session_start_time: Optional[datetime] = None
    session_end_time: Optional[datetime] = None
    session_status: Optional[str] = None # 'Completed', 'Abandoned', 'Error'
    # Potentially allow updating demographics/baseline if needed, add fields here

# Schema for data returned by the API representing a consent/session
class ConsentRead(ConsentBase):
    session_uuid: uuid.UUID
    participant_uuid: uuid.UUID
    recruitment_timestamp: datetime
    consent_timestamp: Optional[datetime]
    assigned_app: Optional[str]
    assigned_paper: Optional[str]
    session_start_time: Optional[datetime]
    session_end_time: Optional[datetime]
    session_status: Optional[str]

    # Optional: Include participant details in the response
    # participant: Optional[ParticipantRead] = None # Uncomment if needed

    class Config:
        orm_mode = True # Pydantic V1 compatibility, use from_attributes in V2
        # from_attributes = True # Pydantic V2 setting


# Now, resolve the forward reference in ParticipantReadWithConsents
# This tells Pydantic how to handle the string reference defined earlier.
# In Pydantic V2, model_rebuild() is used. In V1, update_forward_refs() was common.
# Assuming Pydantic V2+ style for modern FastAPI:
from .participant import ParticipantReadWithConsents
ParticipantReadWithConsents.model_rebuild()
# If using Pydantic V1, you might need:
# ParticipantReadWithConsents.update_forward_refs(ConsentRead=ConsentRead)