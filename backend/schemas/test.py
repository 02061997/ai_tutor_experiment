# backend/schemas/test.py

import uuid
from datetime import datetime
from pydantic import BaseModel, Field
from typing import Optional, Dict, Any, List

# --- Schemas for Final Test Responses ---

# Base schema with core answer data
class FinalTestResponseBase(BaseModel):
    question_id: str = Field(..., description="Identifier for the test question")
    user_answer: Dict[str, Any] = Field(..., description="User's answer(s) stored flexibly")
    time_per_question_ms: Optional[int] = Field(default=None, description="Time spent on the question in milliseconds (optional, from frontend)")

# Schema for creating a single response record (used within the submission batch)
# Represents the data expected from the frontend for ONE question.
class FinalTestResponseCreate(FinalTestResponseBase):
    # session_uuid will be added by the endpoint/service based on the URL path
    # response_id, answer_timestamp, is_correct are handled by backend
    pass

# Schema representing the entire submission from the frontend final test form
class FinalTestSubmission(BaseModel):
    answers: List[FinalTestResponseCreate] = Field(..., description="List of answers for all questions in the final test")

# Schema for reading a final test response record from the API/DB
class FinalTestResponseRead(FinalTestResponseBase):
    response_id: uuid.UUID
    session_uuid: uuid.UUID
    answer_timestamp: datetime
    is_correct: Optional[bool] # Include correctness if stored

    class Config:
        from_attributes = True # Pydantic V2 config (replaces orm_mode)