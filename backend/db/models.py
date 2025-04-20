# backend/db/models.py
# Corrected version 3 (REMOVED all manual index definitions on FK columns)

import uuid
from datetime import datetime
from typing import List, Optional, Dict, Any

# Ensure all needed types are imported from sqlalchemy
from sqlalchemy import Column, JSON, Index, Float, Text, String, Boolean
from sqlalchemy.ext.mutable import MutableDict, MutableList
from sqlmodel import SQLModel, Field, Relationship
from sqlalchemy import Text

# Helper function for default UUIDs
def generate_uuid():
    return uuid.uuid4()

# Helper function for default datetimes
def generate_utcnow():
    return datetime.utcnow()

# ---------------------------------------------
# Participant Model
# ---------------------------------------------
class Participant(SQLModel, table=True):
    participant_uuid: uuid.UUID = Field(
        default_factory=generate_uuid,
        primary_key=True,
        index=True, # Keep index on PK
        nullable=False,
    )
    created_at: datetime = Field(default_factory=generate_utcnow, nullable=False)
    consents: List["Consent"] = Relationship(back_populates="participant")

# ---------------------------------------------
# Consent Model (Represents a participant's session and consent)
# ---------------------------------------------
class Consent(SQLModel, table=True):
    session_uuid: uuid.UUID = Field(
        default_factory=generate_uuid,
        primary_key=True,
        index=True, # Keep index on PK
        nullable=False,
    )
    # REMOVED index=True from participant_uuid (FK)
    participant_uuid: uuid.UUID = Field(
        foreign_key="participant.participant_uuid", nullable=False
    )
    recruitment_timestamp: datetime = Field(default_factory=generate_utcnow, nullable=False)
    consent_timestamp: Optional[datetime] = Field(default=None)
    demographics: Optional[Dict[str, Any]] = Field(default=None, sa_column=Column(JSON))
    baseline_data: Optional[Dict[str, Any]] = Field(default=None, sa_column=Column(JSON))
    assigned_app: Optional[str] = Field(default=None)
    assigned_paper: Optional[str] = Field(default=None)
    session_start_time: Optional[datetime] = Field(default=None)
    session_end_time: Optional[datetime] = Field(default=None)
    session_status: Optional[str] = Field(default=None)

    participant: Participant = Relationship(back_populates="consents")
    survey_responses: List["SurveyResponse"] = Relationship(back_populates="consent_session")
    interaction_logs: List["InteractionLog"] = Relationship(back_populates="consent_session")
    quiz_attempts: List["QuizAttemptState"] = Relationship(back_populates="consent_session")

    # REMOVED explicit Index for participant_uuid from __table_args__
    # __table_args__ = () # Can remove line if empty

# ---------------------------------------------
# Survey Response Model
# ---------------------------------------------
class SurveyResponse(SQLModel, table=True):
    response_id: uuid.UUID = Field(
        default_factory=generate_uuid, primary_key=True, index=True # Keep index on PK
    )
    # REMOVED index=True from session_uuid (FK)
    session_uuid: uuid.UUID = Field(
        foreign_key="consent.session_uuid", nullable=False
    )
    survey_type: str = Field(index=True, nullable=False) # Keep this inline index
    start_time: datetime = Field(default_factory=generate_utcnow, nullable=False)
    end_time: Optional[datetime] = Field(default=None)
    responses: Dict[str, Any] = Field(default={}, sa_column=Column(MutableDict.as_mutable(JSON)))

    consent_session: Consent = Relationship(back_populates="survey_responses")

    # REMOVED explicit Index for session_uuid from __table_args__
    # __table_args__ = () # Can remove line if empty

# ---------------------------------------------
# Interaction Log Model (Heatmap, PDF, etc.)
# ---------------------------------------------
class InteractionLog(SQLModel, table=True):
    interaction_id: uuid.UUID = Field(
        default_factory=generate_uuid, primary_key=True, index=True # Keep index on PK
    )
    # REMOVED index=True from session_uuid (FK)
    session_uuid: uuid.UUID = Field(
        foreign_key="consent.session_uuid", nullable=False
    )
    timestamp: datetime = Field(default_factory=generate_utcnow, index=True, nullable=False) # Keep this index
    event_type: str = Field(index=True, nullable=False) # Keep this index
    target_element_id: Optional[str] = Field(default=None)
    pdf_url: Optional[str] = Field(default=None)
    payload: Dict[str, Any] = Field(default={}, sa_column=Column(MutableDict.as_mutable(JSON)))
    element_width: Optional[int] = Field(default=None)
    element_height: Optional[int] = Field(default=None)

    consent_session: Consent = Relationship(back_populates="interaction_logs")

    # REMOVED explicit Index for session_uuid and timestamp from __table_args__
    # Kept explicit timestamp index inline on Field above now.
    __table_args__ = (
         Index("ix_interactionlog_session_uuid", "session_uuid"), # Let's try putting FK index back explicitly ONLY here
         # Index("ix_interactionlog_timestamp", "timestamp"), # Defined inline
         # Index("ix_interactionlog_event_type", "event_type"), # Defined inline
     )
    # --- Correction: Let's remove ALL explicit FK indexes from __table_args__ as well for now ---
    # __table_args__ = ()


# ---------------------------------------------
# Quiz Question Model (Item Bank)
# ---------------------------------------------
class QuizQuestion(SQLModel, table=True):
    question_id: uuid.UUID = Field(
        default_factory=generate_uuid, primary_key=True, index=True # Keep index on PK
    )
    question_text: str = Field(sa_column=Column(Text))
    options: List[str] = Field(default=[], sa_column=Column(MutableList.as_mutable(JSON)))
    correct_answers: List[int] = Field(default=[], sa_column=Column(MutableList.as_mutable(JSON)))
    irt_parameters: Dict[str, float] = Field(default={}, sa_column=Column(MutableDict.as_mutable(JSON)))
    topic_tags: Optional[List[str]] = Field(default=None, sa_column=Column(MutableList.as_mutable(JSON)))

# ---------------------------------------------
# Quiz Attempt State Model (Tracking participant progress)
# ---------------------------------------------
class QuizAttemptState(SQLModel, table=True):
    attempt_id: uuid.UUID = Field(
        default_factory=generate_uuid, primary_key=True, index=True # Keep index on PK
    )
    # REMOVED index=True from session_uuid (FK)
    session_uuid: uuid.UUID = Field(
        foreign_key="consent.session_uuid", nullable=False
    )
    quiz_id: Optional[str] = Field(default=None, index=True) # Keep this inline index
    start_time: datetime = Field(default_factory=generate_utcnow, nullable=False)
    last_update_time: datetime = Field(default_factory=generate_utcnow, nullable=False)
    current_theta: Optional[float] = Field(default=None, sa_column=Column(Float))
    current_se: Optional[float] = Field(default=None, sa_column=Column(Float))
    administered_items: List[str] = Field(default=[], sa_column=Column(MutableList.as_mutable(JSON)))
    responses: List[int] = Field(default=[], sa_column=Column(MutableList.as_mutable(JSON)))
    is_complete: bool = Field(default=False, index=True) # Keep this inline index
    final_score_percent: Optional[float] = Field(default=None, sa_column=Column(Float))
    identified_weak_topics: Optional[List[str]] = Field(default=None, sa_column=Column(MutableList.as_mutable(JSON)))

    consent_session: Consent = Relationship(back_populates="quiz_attempts")

    # REMOVED explicit Index for session_uuid from __table_args__
    # __table_args__ = () # Can remove line if empty

# ---------------------------------------------
# Researcher Model (NEW - Added for Authentication)
# ---------------------------------------------
class Researcher(SQLModel, table=True):
    researcher_id: uuid.UUID = Field(
        default_factory=generate_uuid,
        primary_key=True,
        index=True, # Keep index on PK
        nullable=False,
    )
    # Keep index defined inline via Column unique=True, index=True
    email: str = Field(
        sa_column=Column(String, unique=True, index=True),
        description="Researcher's email/login username"
    )
    hashed_password: str = Field(nullable=False)
    full_name: Optional[str] = Field(default=None)
    is_active: bool = Field(sa_column=Column(Boolean, default=True))
    created_at: datetime = Field(default_factory=generate_utcnow, nullable=False)


# --- Add this class to backend/db/models.py ---

# ---------------------------------------------
# Final Test Response Model
# ---------------------------------------------
class FinalTestResponse(SQLModel, table=True):
    response_id: uuid.UUID = Field(
        default_factory=generate_uuid,
        primary_key=True,
        index=True,
        nullable=False,
    )
    session_uuid: uuid.UUID = Field(
        foreign_key="consent.session_uuid", nullable=False # Foreign key link
        # No index=True here, let DB handle FK indexing or define explicitly below if needed
    )
    # Identifier for the question in the final test
    question_id: str = Field(index=True, nullable=False)
    # Store the user's answer flexibly (could be text, number, selected choice)
    user_answer: Dict[str, Any] = Field(default={}, sa_column=Column(MutableDict.as_mutable(JSON)))
    # Correctness might be evaluated later or not applicable for all questions
    is_correct: Optional[bool] = Field(default=None)
    # Timestamp when this specific answer was submitted/recorded
    answer_timestamp: datetime = Field(default_factory=generate_utcnow, nullable=False)
    # Optional: Time spent on this question (calculated by frontend)
    time_per_question_ms: Optional[int] = Field(default=None)

    # Relationship back to Consent (optional but potentially useful)
    # consent_session: Consent = Relationship() # Needs back_populates on Consent if added

    # Define indexes explicitly if needed, avoiding inline index=True for FKs
    __table_args__ = (
        Index("ix_finaltestresponse_session_uuid", "session_uuid"),
        # Index("ix_finaltestresponse_question_id", "question_id"), # Covered by inline index=True
    )

# ---------------------------------------------
# App1 Interaction Log Model
# ---------------------------------------------
class App1InteractionLog(SQLModel, table=True):
    log_id: uuid.UUID = Field(
        default_factory=generate_uuid,
        primary_key=True,
        index=True,
        nullable=False,
    )
    session_uuid: uuid.UUID = Field(
        foreign_key="consent.session_uuid", nullable=False # Foreign key link
        # Index defined below
    )
    log_timestamp: datetime = Field(
        default_factory=generate_utcnow, nullable=False, index=True
    )
    event_type: str = Field(
        index=True, nullable=False,
        description="Type of event: UserPrompt, LlmResponse, SystemMessage, Error" # [cite: 14]
    )
    # Use Text for potentially long prompts/responses/errors
    prompt_text: Optional[str] = Field(default=None, sa_column=Column(Text)) # [cite: 14]
    response_text: Optional[str] = Field(default=None, sa_column=Column(Text)) # [cite: 15]
    error_details: Optional[str] = Field(default=None, sa_column=Column(Text)) # [cite: 17]
    # Optional metrics if available from API
    token_count_prompt: Optional[int] = Field(default=None) # [cite: 15]
    token_count_response: Optional[int] = Field(default=None) # [cite: 16]
    llm_response_time_ms: Optional[int] = Field(default=None) # [cite: 16]
    llm_time_to_first_token_ms: Optional[int] = Field(default=None) # [cite: 17]

    # Relationship back to Consent (optional but potentially useful)
    # consent_session: Consent = Relationship() # Needs configuration if added

    # Define indexes explicitly if needed
    __table_args__ = (
        Index("ix_app1interactionlog_session_uuid", "session_uuid"),
        # Indexes for event_type and timestamp are defined inline on Field
    )