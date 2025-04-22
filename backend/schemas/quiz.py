# backend/schemas/quiz.py
import uuid
from uuid import UUID
from datetime import datetime
from pydantic import BaseModel, Field, ConfigDict # Ensure these are imported
from typing import Dict, Any, Optional, List, Union # Ensure Optional, List are import

# ---------------------------------------------
# === SCHEMAS FOR RAG/LLM GENERATED QUIZ ===
# ---------------------------------------------

class GeneratedMCQForParticipant(BaseModel):
    """
    Schema for sending a generated MCQ question OR completion/error status
    to the participant. Fields related to the question are optional.
    """

    mcq_id: Optional[UUID] = None
    question: Optional[str] = None             # ← renamed
    options: Optional[List[str]] = None
    quiz_complete: bool = False
    error: Optional[str] = None

    model_config = ConfigDict(
        from_attributes=True,
        populate_by_name=True,
    )


class GeneratedMCQAnswerInput(BaseModel):
    """Schema for receiving an answer from the participant for a generated MCQ."""
    mcq_id: uuid.UUID = Field(..., description="The ID of the generated question being answered")
    chosen_answer_letter: str = Field(..., pattern="^[A-Da-d]$", description="The letter (A, B, C, D) chosen by the user") # Allow lowercase input too
    timestamp_frontend: Optional[datetime] = Field(default=None, alias="timestamp") # Optional frontend timestamp

    # Optional validation to ensure letter is uppercase for consistency if needed downstream
    # @field_validator('chosen_answer_letter')
    # def uppercase_letter(cls, v):
    #     return v.upper()

    model_config = ConfigDict(from_attributes=True) # Example for V2 config if needed elsewhere


class GeneratedMCQAnswerFeedback(BaseModel):
    """Schema for the response after submitting an answer for a generated MCQ."""
    is_correct: bool
    correct_answer_letter: str = Field(..., pattern="^[A-D]$", description="The correct answer letter (A, B, C, or D)")
    explanation: str
    quiz_complete: bool # Added field to signal if quiz is now finished

    model_config = ConfigDict(from_attributes=True)

# Note: You might have other schemas here from previous versions.
# Ensure the schemas used by your current endpoints and services match these definitions.