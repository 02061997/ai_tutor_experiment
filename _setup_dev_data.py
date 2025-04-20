# backend/db/models.py
# Corrected version (Removed nullable=False where sa_column is used)

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
# Participant Model
# ---------------------------------------------
class Participant(SQLModel, table=True):
    participant_uuid: uuid.UUID = Field(
        default_factory=generate_uuid,
        primary_key=True,
        index=True,
        nullable=False,
    )
    created_at: datetime = Field(default_factory=generate_utcnow, nullable=False)

    # Relationships
    consents: List["Consent"] = Relationship(back_populates="participant")

# ---------------------------------------------
# Consent Model (Represents a participant's session and consent)
# ---------------------------------------------
class Consent(SQLModel, table=True):
    session_uuid: uuid.UUID = Field(
        default_factory=generate_uuid,
        primary_key=True,
        index=True,
        nullable=False,
    )
    participant_uuid: uuid.UUID = Field(
        foreign_key="participant.participant_uuid", index=True, nullable=False
    )
    recruitment_timestamp: datetime = Field(default_factory=generate_utcnow, nullable=False) # Phase 1
    consent_timestamp: Optional[datetime] = Field(default=None) # Phase 1
    demographics: Optional[Dict[str, Any]] = Field(default=None, sa_column=Column(JSON)) # Phase 1
    baseline_data: Optional[Dict[str, Any]] = Field(default=None, sa_column=Column(JSON)) # Phase 1
    assigned_app: Optional[str] = Field(default=None) # 'App1' or 'App2'
    assigned_paper: Optional[str] = Field(default=None) # 'Paper1' or 'Paper2'
    session_start_time: Optional[datetime] = Field(default=None) # Phase 1
    session_end_time: Optional[datetime] = Field(default=None) # Phase 5
    session_status: Optional[str] = Field(default=None) # 'Completed', 'Abandoned', 'Error'

    # Relationships
    participant: Participant = Relationship(back_populates="consents")
    survey_responses: List["SurveyResponse"] = Relationship(back_populates="consent_session")
    interaction_logs: List["InteractionLog"] = Relationship(back_populates="consent_session")
    quiz_attempts: List["QuizAttemptState"] = Relationship(back_populates="consent_session")

    __table_args__ = (
        Index("ix_consent_participant_uuid", "participant_uuid"),
    )

# ---------------------------------------------
# Survey Response Model
# ---------------------------------------------
class SurveyResponse(SQLModel, table=True):
    response_id: uuid.UUID = Field(
        default_factory=generate_uuid, primary_key=True, index=True
    )
    session_uuid: uuid.UUID = Field(
        foreign_key="consent.session_uuid", index=True, nullable=False
    )
    survey_type: str = Field(index=True, nullable=False)
    start_time: datetime = Field(default_factory=generate_utcnow, nullable=False) # Phase 4b, 4c
    end_time: Optional[datetime] = Field(default=None) # Phase 4b, 4c
    responses: Dict[str, Any] = Field(default={}, sa_column=Column(MutableDict.as_mutable(JSON))) # Phase 4b, 4c

    # Relationships
    consent_session: Consent = Relationship(back_populates="survey_responses")

    __table_args__ = (
        Index("ix_surveyresponse_session_uuid", "session_uuid"),
        Index("ix_surveyresponse_survey_type", "survey_type"),
    )

# ---------------------------------------------
# Interaction Log Model (Heatmap, PDF, etc.)
# ---------------------------------------------
class InteractionLog(SQLModel, table=True):
    interaction_id: uuid.UUID = Field(
        default_factory=generate_uuid, primary_key=True, index=True
    )
    session_uuid: uuid.UUID = Field(
        foreign_key="consent.session_uuid", index=True, nullable=False
    )
    timestamp: datetime = Field(default_factory=generate_utcnow, index=True, nullable=False) # Table 2, Table 3
    event_type: str = Field(index=True, nullable=False) # Table 2, Table 3 ('click', 'pdf_page_view', etc.)
    target_element_id: Optional[str] = Field(default=None) # Table 2
    pdf_url: Optional[str] = Field(default=None) # For PDF events, Table 3
    payload: Dict[str, Any] = Field(default={}, sa_column=Column(MutableDict.as_mutable(JSON))) # Table 2, Table 3 (coords, scroll%, text)
    element_width: Optional[int] = Field(default=None) # Table 2, Table 3
    element_height: Optional[int] = Field(default=None) # Table 2, Table 3

    # Relationships
    consent_session: Consent = Relationship(back_populates="interaction_logs")

    __table_args__ = (
        Index("ix_interactionlog_session_uuid", "session_uuid"),
        Index("ix_interactionlog_timestamp", "timestamp"),
        Index("ix_interactionlog_event_type", "event_type"),
    )

# ---------------------------------------------
# Quiz Question Model (Item Bank)
# ---------------------------------------------
class QuizQuestion(SQLModel, table=True):
    question_id: uuid.UUID = Field(
        default_factory=generate_uuid, primary_key=True, index=True
    )
    # Using Text type for potentially long question text
    # REMOVED nullable=False from Field()
    question_text: str = Field(sa_column=Column(Text)) # Table 5
    options: List[str] = Field(default=[], sa_column=Column(MutableList.as_mutable(JSON))) # Table 5
    # List of 0-based indices of correct options
    correct_answers: List[int] = Field(default=[], sa_column=Column(MutableList.as_mutable(JSON))) # Table 5
    # Storing IRT parameters: {"a": float, "b": float, "c": float}
    irt_parameters: Dict[str, float] = Field(default={}, sa_column=Column(MutableDict.as_mutable(JSON))) # Table 5
    # Optional tags for content balancing or topic identification
    topic_tags: Optional[List[str]] = Field(default=None, sa_column=Column(MutableList.as_mutable(JSON))) # Table 5

# ---------------------------------------------
# Quiz Attempt State Model (Tracking participant progress)
# ---------------------------------------------
class QuizAttemptState(SQLModel, table=True):
    attempt_id: uuid.UUID = Field(
        default_factory=generate_uuid, primary_key=True, index=True
    )
    session_uuid: uuid.UUID = Field(
        foreign_key="consent.session_uuid", index=True, nullable=False
    )
    quiz_id: Optional[str] = Field(default=None, index=True) # Table 6
    start_time: datetime = Field(default_factory=generate_utcnow, nullable=False) # Table 6
    last_update_time: datetime = Field(default_factory=generate_utcnow, nullable=False) # Table 6
    current_theta: Optional[float] = Field(default=None, sa_column=Column(Float)) # Table 6
    current_se: Optional[float] = Field(default=None, sa_column=Column(Float)) # Table 6
    administered_items: List[str] = Field(default=[], sa_column=Column(MutableList.as_mutable(JSON))) # Table 6
    responses: List[int] = Field(default=[], sa_column=Column(MutableList.as_mutable(JSON))) # Table 6
    is_complete: bool = Field(default=False, index=True) # Table 6
    final_score_percent: Optional[float] = Field(default=None, sa_column=Column(Float)) # Phase 3b
    identified_weak_topics: Optional[List[str]] = Field(default=None, sa_column=Column(MutableList.as_mutable(JSON))) # Phase 3b

    # Relationships
    consent_session: Consent = Relationship(back_populates="quiz_attempts")

    __table_args__ = (
        Index("ix_quizattemptstate_session_uuid", "session_uuid"),
        Index("ix_quizattemptstate_is_complete", "is_complete"),
    )

# ---------------------------------------------
# Researcher Model (NEW - Added for Authentication)
# ---------------------------------------------
class Researcher(SQLModel, table=True):
    researcher_id: uuid.UUID = Field(
        default_factory=generate_uuid,
        primary_key=True,
        index=True,
        nullable=False,
    )
    # REMOVED nullable=False from Field()
    email: str = Field(
        sa_column=Column(String, unique=True, index=True),
        description="Researcher's email/login username"
    )
    hashed_password: str = Field(nullable=False)
    full_name: Optional[str] = Field(default=None)
    # Moved default=True into Column, removed from Field()
    is_active: bool = Field(sa_column=Column(Boolean, default=True))
    created_at: datetime = Field(default_factory=generate_utcnow, nullable=False)