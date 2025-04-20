# ai_tutor_experiment/backend/schemas/interaction.py
# Contains Pydantic schemas for both App2 (UI/PDF) and App1 (LLM Chat) interaction logs,
# as well as schemas for the App1 LLM API endpoint request/response.

import uuid
from datetime import datetime
from pydantic import BaseModel, Field
from typing import Dict, Any, Optional, List

# ---------------------------------------------
# Schemas for App2 Interaction Logs (UI, PDF, Heatmap)
# ---------------------------------------------

class InteractionLogBase(BaseModel):
    """
    Base schema for App2 interaction log entries (UI events, PDF interactions).
    Contains common fields describing the interaction context.
    Corresponds to data points in Tables 2 & 3 of the plan.
    """
    # Type of interaction event (e.g., 'click', 'pdf_page_view', 'scroll_depth')
    event_type: str = Field(..., description="Type of interaction event (e.g., 'click', 'pdf_page_view')")
    # Optional identifier of the specific HTML element interacted with (e.g., 'pdf-viewer-area', 'quiz-submit-button')
    target_element_id: Optional[str] = Field(default=None, description="Identifier of the HTML element interacted with")
    # Optional URL or identifier for PDF-specific events
    pdf_url: Optional[str] = Field(default=None, description="URL or identifier of the PDF for PDF events")
    # Flexible JSON payload holding event-specific data (e.g., coordinates, scroll percentage, selected text)
    payload: Dict[str, Any] = Field(default={}, description="Event-specific data (coordinates, scroll%, text, etc.)")
    # Optional dimensions of the target element at the time of interaction, useful for normalization
    element_width: Optional[int] = Field(default=None, description="Width of target element at interaction time (optional)")
    element_height: Optional[int] = Field(default=None, description="Height of target element at interaction time (optional)")
    # Note: session_uuid is typically handled by the API endpoint context (path parameter).
    # Note: Backend timestamp is usually added by the service/endpoint upon receiving the log.

class InteractionLogCreate(InteractionLogBase):
    """
    Schema used when creating a *single* App2 interaction log entry.
    Represents the data structure sent from the frontend tracker modules within a batch.
    """
    # Optional: Frontend might provide its own timestamp if precise client-side timing is crucial for analysis.
    # The backend should still record its own timestamp upon receipt.
    timestamp_frontend: Optional[datetime] = Field(
        default=None,
        alias="timestamp", # Allows frontend to send 'timestamp' key, maps to 'timestamp_frontend'
        description="Optional timestamp from frontend if precise client-side timing is needed"
    )
    # Inherits fields from InteractionLogBase

class InteractionLogCreateBatch(BaseModel):
    """
    Schema for receiving a *batch* of App2 interaction logs from the frontend.
    The frontend should buffer logs and send them periodically using this structure.
    """
    # A list containing multiple individual log entries
    logs: List[InteractionLogCreate]

class InteractionLogRead(InteractionLogBase):
    """
    Schema used when reading/returning an App2 interaction log entry from the API/database.
    Includes database-generated fields.
    """
    interaction_id: uuid.UUID # Primary key of the log entry
    session_uuid: uuid.UUID   # Session this log belongs to
    timestamp: datetime       # Backend-generated timestamp when the log was processed/saved

    class Config:
        """Pydantic configuration."""
        from_attributes = True # Enable creating schema from ORM objects (Pydantic V2)

# ---------------------------------------------
# Schemas for App1 Interaction Logs (LLM Chat)
# ---------------------------------------------

class App1InteractionLogBase(BaseModel):
    """
    Base schema for App1 interaction log entries (LLM chat events).
    Contains fields specific to logging prompts, responses, errors, and performance metrics.
    Corresponds to data points in Phase 2, App1 of the plan.
    """
    # Type of event being logged
    event_type: str = Field(..., description="Type: UserPrompt, LlmResponse, SystemMessage, Error")
    # Text of the user's prompt (relevant for UserPrompt, LlmResponse, Error event types)
    prompt_text: Optional[str] = Field(default=None, description="Text of the user's prompt to the LLM")
    # Text of the LLM's response (relevant for LlmResponse event type)
    response_text: Optional[str] = Field(default=None, description="Text of the LLM's response")
    # Details if an error occurred during the LLM call (relevant for Error event type)
    error_details: Optional[str] = Field(default=None, description="Details if an error occurred during LLM interaction")
    # Optional metrics if available from the LLM API (e.g., Groq)
    token_count_prompt: Optional[int] = Field(default=None, description="Token count for the prompt (if available)")
    token_count_response: Optional[int] = Field(default=None, description="Token count for the response (if available)")
    llm_response_time_ms: Optional[int] = Field(default=None, description="Total time for LLM response generation in ms (if measured)")
    llm_time_to_first_token_ms: Optional[int] = Field(default=None, description="Time to first token in ms (if measured)")

class App1InteractionLogCreate(App1InteractionLogBase):
    """
    Schema used when creating a *single* App1 interaction log entry.
    Represents the data the backend service will assemble to log an event.
    """
    # session_uuid will be added by the endpoint/service based on the URL path or context.
    # log_id and log_timestamp are handled by the backend/database defaults.
    pass # Inherits all fields from App1InteractionLogBase

class App1InteractionLogRead(App1InteractionLogBase):
    """
    Schema used when reading/returning an App1 interaction log entry from the API/database.
    Includes database-generated fields.
    """
    log_id: uuid.UUID       # Primary key of the log entry
    session_uuid: uuid.UUID # Session this log belongs to
    log_timestamp: datetime # Backend-generated timestamp when the log was saved

    class Config:
        """Pydantic configuration."""
        from_attributes = True # Enable creating schema from ORM objects (Pydantic V2)

# ---------------------------------------------
# Schemas for App1 LLM Interaction Endpoint
# ---------------------------------------------

class App1LlmPromptRequest(BaseModel):
    """
    Schema for the request body sent *to* the backend endpoint
    that triggers an App1 LLM call.
    """
    prompt: str = Field(..., description="The user prompt text to send to the LLM")
    # Optional: could add other parameters like model selection, temperature etc. here
    # model_override: Optional[str] = None

class App1LlmResponse(BaseModel):
    """
    Schema for the response body sent *from* the backend endpoint
    after successfully getting a reply from the App1 LLM.
    """
    response_text: str = Field(..., description="The text response generated by the LLM")
    # Optional: could include token usage or other metadata if needed by frontend
    # token_usage: Optional[Dict[str, int]] = None