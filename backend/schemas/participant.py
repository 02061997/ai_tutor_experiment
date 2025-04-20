# backend/schemas/participant.py

import uuid
from datetime import datetime
from pydantic import BaseModel, Field
from typing import List, Optional

# Forward declaration for ConsentRead schema to handle circular dependency if needed
# This might not be strictly necessary depending on final structure, but good practice.
# from .consent import ConsentRead # Avoid direct import for now, use List['ConsentRead'] string

# Base Schema (currently empty, might add fields later if needed)
class ParticipantBase(BaseModel):
    pass

# Schema for creating a participant (not needed if created implicitly via Consent)
# class ParticipantCreate(ParticipantBase):
#     pass

# Schema for reading participant data (returned by API)
class ParticipantRead(ParticipantBase):
    participant_uuid: uuid.UUID
    created_at: datetime

    class Config:
        orm_mode = True # Pydantic V1 compatibility, use from_attributes in V2
        # from_attributes = True # Pydantic V2 setting

# Schema for reading participant data along with their consent sessions
class ParticipantReadWithConsents(ParticipantRead):
    # Use forward reference string to avoid circular import errors at runtime
    consents: List['ConsentRead'] = [] # Default to empty list


# Need to update ConsentRead schema definition later to avoid circular import errors
# This is often handled by updating the forward references after all models are defined
# or by careful structuring. We'll manage this when defining ConsentRead.