# backend/db/models.py


import uuid
from datetime import datetime
from typing import List, Optional, Dict, Any

# Ensure all needed types are imported from sqlalchemy
from sqlalchemy import Column, JSON, Index, Float, Text, String, Boolean
from sqlalchemy.ext.mutable import MutableDict, MutableList
from sqlmodel import SQLModel, Field, Relationship


# Helper function for default UUIDs
def generate_uuid():
    return uuid.uuid4()

# Helper function for default datetimes
def generate_utcnow():
    return datetime.utcnow()

# ---------------------------------------------
# Participant Model (Existing)
# ---------------------------------------------
class Participant(SQLModel, table=True):
    participant_uuid: uuid.UUID = Field(
        default_factory=generate_uuid, primary_key=True, index=True, nullable=False
    )
    created_at: datetime = Field(default_factory=generate_utcnow, nullable=False)
    consents: List["Consent"] = Relationship(back_populates="participant")

# ---------------------------------------------
# Consent Model (Existing - Removed relationship to old QuizAttemptState)
# ---------------------------------------------
class Consent(SQLModel, table=True):
    session_uuid: uuid.UUID = Field(
        default_factory=generate_uuid, primary_key=True, index=True, nullable=False
    )
    participant_uuid: uuid.UUID = Field(foreign_key="participant.participant_uuid", nullable=False)
    recruitment_timestamp: datetime = Field(default_factory=generate_utcnow, nullable=False)
    consent_timestamp: Optional[datetime] = Field(default=None)
    demographics: Optional[Dict[str, Any]] = Field(default=None, sa_column=Column(JSON))
    baseline_data: Optional[Dict[str, Any]] = Field(default=None, sa_column=Column(JSON))
    assigned_app: Optional[str] = Field(default=None)
    assigned_paper: Optional[str] = Field(default=None)
    session_start_time: Optional[datetime] = Field(default=None)
    session_end_time: Optional[datetime] = Field(default=None)
    session_status: Optional[str] = Field(default=None)

    # Relationships
    participant: Participant = Relationship(back_populates="consents")
    survey_responses: List["SurveyResponse"] = Relationship(back_populates="consent_session")
    interaction_logs: List["InteractionLog"] = Relationship(back_populates="consent_session")
    # --- REMOVED Obsolete Relationship ---
    # quiz_attempts: List["QuizAttemptState"] = Relationship(back_populates="consent_session")
    # --- END REMOVED ---
    # --- NEW Relationships for RAG Quiz ---
    generated_mcqs: List["GeneratedMCQ"] = Relationship(back_populates="consent_session")
    mcq_attempts: List["MCQAttempt"] = Relationship(back_populates="consent_session")
    # --- END NEW Relationships ---


# ---------------------------------------------
# Survey Response Model (Existing)
# ---------------------------------------------
class SurveyResponse(SQLModel, table=True):
    response_id: uuid.UUID = Field(default_factory=generate_uuid, primary_key=True, index=True)
    session_uuid: uuid.UUID = Field(foreign_key="consent.session_uuid", nullable=False)
    survey_type: str = Field(index=True, nullable=False)
    start_time: datetime = Field(default_factory=generate_utcnow, nullable=False)
    end_time: Optional[datetime] = Field(default=None)
    responses: Dict[str, Any] = Field(default={}, sa_column=Column(MutableDict.as_mutable(JSON)))
    consent_session: Consent = Relationship(back_populates="survey_responses")

# ---------------------------------------------
# Interaction Log Model (Existing)
# ---------------------------------------------
class InteractionLog(SQLModel, table=True):
    interaction_id: uuid.UUID = Field(default_factory=generate_uuid, primary_key=True, index=True)
    session_uuid: uuid.UUID = Field(foreign_key="consent.session_uuid", nullable=False, index=True) # Add index back here
    timestamp: datetime = Field(default_factory=generate_utcnow, index=True, nullable=False)
    event_type: str = Field(index=True, nullable=False)
    target_element_id: Optional[str] = Field(default=None)
    pdf_url: Optional[str] = Field(default=None)
    payload: Dict[str, Any] = Field(default={}, sa_column=Column(MutableDict.as_mutable(JSON)))
    element_width: Optional[int] = Field(default=None)
    element_height: Optional[int] = Field(default=None)
    consent_session: Consent = Relationship(back_populates="interaction_logs")



# ---------------------------------------------
# Researcher Model (Existing)
# ---------------------------------------------
class Researcher(SQLModel, table=True):
    researcher_id: uuid.UUID = Field(default_factory=generate_uuid, primary_key=True, index=True, nullable=False)
    email: str = Field(sa_column=Column(String, unique=True, index=True), description="Researcher's email/login username")
    hashed_password: str = Field(nullable=False)
    full_name: Optional[str] = Field(default=None)
    is_active: bool = Field(sa_column=Column(Boolean, default=True))
    created_at: datetime = Field(default_factory=generate_utcnow, nullable=False)

# ---------------------------------------------
# Final Test Response Model (Existing)
# ---------------------------------------------
class FinalTestResponse(SQLModel, table=True):
    response_id: uuid.UUID = Field(default_factory=generate_uuid, primary_key=True, index=True, nullable=False)
    session_uuid: uuid.UUID = Field(foreign_key="consent.session_uuid", nullable=False, index=True)
    question_id: str = Field(index=True, nullable=False)
    user_answer: Dict[str, Any] = Field(default={}, sa_column=Column(MutableDict.as_mutable(JSON)))
    is_correct: Optional[bool] = Field(default=None)
    answer_timestamp: datetime = Field(default_factory=generate_utcnow, nullable=False)
    time_per_question_ms: Optional[int] = Field(default=None)
    # Define __table_args__ separately if needed, index inline is fine too
    # __table_args__ = (Index("ix_finaltestresponse_session_uuid", "session_uuid"),)


# ---------------------------------------------
# App1 Interaction Log Model (Existing)
# ---------------------------------------------
class App1InteractionLog(SQLModel, table=True):
    log_id: uuid.UUID = Field(default_factory=generate_uuid, primary_key=True, index=True, nullable=False)
    session_uuid: uuid.UUID = Field(foreign_key="consent.session_uuid", nullable=False, index=True)
    log_timestamp: datetime = Field(default_factory=generate_utcnow, nullable=False, index=True)
    event_type: str = Field(index=True, nullable=False, description="UserPrompt, LlmResponse, SystemMessage, Error")
    prompt_text: Optional[str] = Field(default=None, sa_column=Column(Text))
    response_text: Optional[str] = Field(default=None, sa_column=Column(Text))
    error_details: Optional[str] = Field(default=None, sa_column=Column(Text))
    token_count_prompt: Optional[int] = Field(default=None)
    token_count_response: Optional[int] = Field(default=None)
    llm_response_time_ms: Optional[int] = Field(default=None)
    llm_time_to_first_token_ms: Optional[int] = Field(default=None)
    # __table_args__ = (Index("ix_app1interactionlog_session_uuid", "session_uuid"),)


# =============================================
# === NEW MODELS FOR RAG/LLM GENERATED QUIZ ===
# =============================================

class GeneratedMCQ(SQLModel, table=True):
    mcq_id: uuid.UUID = Field(default_factory=generate_uuid, primary_key=True, index=True, nullable=False)
    session_uuid: uuid.UUID = Field(foreign_key="consent.session_uuid", nullable=False, index=True)
    paper_id: Optional[str] = Field(default=None, index=True)
    question_text: str = Field(sa_column=Column(Text))
    option_a: str = Field(sa_column=Column(Text))
    option_b: str = Field(sa_column=Column(Text))
    option_c: str = Field(sa_column=Column(Text))
    option_d: str = Field(sa_column=Column(Text))
    correct_answer_letter: str = Field(sa_column=Column(String(1)))
    explanation: str = Field(sa_column=Column(Text))
    generation_context: Optional[str] = Field(default=None, sa_column=Column(Text))
    created_at: datetime = Field(default_factory=generate_utcnow, nullable=False)
    consent_session: Consent = Relationship(back_populates="generated_mcqs")
    attempts: List["MCQAttempt"] = Relationship(back_populates="generated_mcq")


class MCQAttempt(SQLModel, table=True):
    attempt_id: uuid.UUID = Field(default_factory=generate_uuid, primary_key=True, index=True, nullable=False)
    mcq_id: uuid.UUID = Field(foreign_key="generatedmcq.mcq_id", nullable=False, index=True)
    session_uuid: uuid.UUID = Field(foreign_key="consent.session_uuid", nullable=False, index=True)
    chosen_answer_letter: str = Field(sa_column=Column(String(1)))
    is_correct: bool = Field(nullable=False)
    attempt_timestamp: datetime = Field(default_factory=generate_utcnow, nullable=False)
    generated_mcq: GeneratedMCQ = Relationship(back_populates="attempts")
    consent_session: Consent = Relationship(back_populates="mcq_attempts")
