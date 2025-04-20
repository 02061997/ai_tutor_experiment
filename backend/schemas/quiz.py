# backend/schemas/quiz.py

import uuid
from datetime import datetime
from pydantic import BaseModel, Field, validator
from typing import Dict, Any, Optional, List, Union

# ---------------------------------------------
# Schemas for Quiz Questions (Item Bank)
# ---------------------------------------------

# Base schema for quiz questions
class QuizQuestionBase(BaseModel):
    question_text: str = Field(..., description="The text content of the quiz question") # Table 5
    options: List[str] = Field(..., description="List of possible answer options") # Table 5
    topic_tags: Optional[List[str]] = Field(default=None, description="Optional topic tags for content balancing") # Table 5

# Schema for creating a new quiz question (e.g., via an admin interface)
class QuizQuestionCreate(QuizQuestionBase):
    correct_answers: List[int] = Field(..., description="List of 0-based indices for the correct option(s)") # Table 5
    # IRT parameters expected as a dictionary: {"a": float, "b": float, "c": float}
    irt_parameters: Dict[str, float] = Field(..., description="IRT parameters (a, b, c)") # Table 5

    @validator('irt_parameters')
    def validate_irt_params(cls, v):
        required_keys = {'a', 'b', 'c'}
        if not isinstance(v, dict):
            raise ValueError("irt_parameters must be a dictionary")
        if not required_keys.issubset(v.keys()):
            raise ValueError(f"irt_parameters must contain keys: {required_keys}")
        for key in required_keys:
            if not isinstance(v[key], (float, int)):
                 raise ValueError(f"IRT parameter '{key}' must be a float or int")
        return v

# Schema for reading a quiz question *including* sensitive info (correct answers, IRT params)
# Use case: internal logic, admin dashboard, potentially data analysis (not for participants)
class QuizQuestionRead(QuizQuestionBase):
    question_id: uuid.UUID
    correct_answers: List[int] # Included for internal use/verification
    irt_parameters: Dict[str, float] # Included for internal use/CAT logic

    class Config:
        orm_mode = True # Pydantic V1
        # from_attributes = True # Pydantic V2

# Schema for sending a quiz question *to the participant* during the quiz
# Excludes sensitive information like correct answers and IRT parameters.
class QuizQuestionForParticipant(BaseModel):
    question_id: uuid.UUID
    question_text: str
    options: List[str]
    # We don't send topic_tags to the participant unless needed for UI reasons

    class Config:
        orm_mode = True # Pydantic V1
        # from_attributes = True # Pydantic V2


# ---------------------------------------------
# Schemas for Quiz Attempt State
# ---------------------------------------------

# Base schema for quiz attempt state
class QuizAttemptStateBase(BaseModel):
    quiz_id: Optional[str] = Field(default=None, description="Identifier if multiple quizzes exist") # Table 6

# Schema for creating a new quiz attempt state (usually minimal input)
class QuizAttemptStateCreate(QuizAttemptStateBase):
    # session_uuid comes from context, other fields have defaults or are set by logic
    pass

# Schema for updating the quiz attempt state (used internally by service)
class QuizAttemptStateUpdate(BaseModel):
    last_update_time: Optional[datetime] = None # Table 6
    current_theta: Optional[float] = None # Table 6
    current_se: Optional[float] = None # Table 6
    administered_items: Optional[List[str]] = None # Table 6 (List of question_id strings)
    responses: Optional[List[int]] = None # Table 6 (List of 0/1)
    is_complete: Optional[bool] = None # Table 6
    final_score_percent: Optional[float] = None # Phase 3b
    identified_weak_topics: Optional[List[str]] = None # Phase 3b


# Schema for reading the full quiz attempt state (returned by API, potentially for admin/debug)
class QuizAttemptStateRead(QuizAttemptStateBase):
    attempt_id: uuid.UUID
    session_uuid: uuid.UUID
    start_time: datetime
    last_update_time: datetime
    current_theta: Optional[float]
    current_se: Optional[float]
    administered_items: List[str] = []
    responses: List[int] = []
    is_complete: bool
    final_score_percent: Optional[float]
    identified_weak_topics: Optional[List[str]] = []

    class Config:
        orm_mode = True # Pydantic V1
        # from_attributes = True # Pydantic V2

# ---------------------------------------------
# Schemas for API Interaction during Quiz
# ---------------------------------------------

# Schema for the participant submitting an answer
class QuizAnswerInput(BaseModel):
    question_id: uuid.UUID = Field(..., description="The ID of the question being answered")
    # Assuming multiple choice where user selects one option index
    selected_option_index: int = Field(..., description="The 0-based index of the selected answer option")
    # Optional: Frontend timestamp if needed for detailed timing analysis
    timestamp_frontend: Optional[datetime] = Field(default=None, alias="timestamp")

# Schema for the response after submitting an answer (contains next question or completion status)
class QuizNextQuestionResponse(BaseModel):
    next_question: Optional[QuizQuestionForParticipant] = Field(default=None, description="The next question to present to the participant, null if quiz is complete")
    is_complete: bool = Field(..., description="Flag indicating if the quiz has ended")
    # Optional fields to provide feedback at the end or potentially during
    current_theta: Optional[float] = Field(default=None, description="Current estimated ability (theta), potentially only sent at end")
    current_se: Optional[float] = Field(default=None, description="Standard error of the theta estimate, potentially only sent at end")
    final_score_percent: Optional[float] = Field(default=None, description="Final score if the quiz is complete") # Phase 3b
    identified_weak_topics: Optional[List[str]] = Field(default=None, description="List of weak topics identified if the quiz is complete") # Phase 3b