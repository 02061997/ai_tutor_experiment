# backend/schemas/survey.py

import uuid
from datetime import datetime
from pydantic import BaseModel, Field
from typing import Dict, Any, Optional

# Base schema with fields common to Create and Read
class SurveyResponseBase(BaseModel):
    survey_type: str = Field(..., description="Type of survey (e.g., 'experience_app1', 'experience_app2', 'exit')") # Phase 4b, 4c
    responses: Dict[str, Any] = Field(..., description="Dictionary containing survey questions and answers") # Phase 4b, 4c

# Schema for data required when creating a new survey response
class SurveyResponseCreate(SurveyResponseBase):
    # session_uuid will be determined from the authenticated context or path parameter
    # response_id, start_time, end_time will be handled by the backend
    pass # Inherits fields from SurveyResponseBase

# Schema for data returned by the API representing a survey response
class SurveyResponseRead(SurveyResponseBase):
    response_id: uuid.UUID
    session_uuid: uuid.UUID
    start_time: datetime
    end_time: Optional[datetime] # May be null if survey is ongoing or abandoned

    class Config:
        orm_mode = True # Pydantic V1 compatibility, use from_attributes in V2
        # from_attributes = True # Pydantic V2 setting