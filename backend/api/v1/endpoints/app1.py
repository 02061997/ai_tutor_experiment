# backend/api/v1/endpoints/app1.py
# Updated version with LLM endpoint

import uuid
from typing import List, Optional

from fastapi import APIRouter, Depends, HTTPException, status
from sqlmodel.ext.asyncio.session import AsyncSession
from groq import APIError # Import potential API error from Groq

# Dependency for DB session
from backend.db.database import get_session

# Service and Schemas specific to App1
from backend.services.app1_service import App1Service
from backend.schemas.interaction import (
    App1InteractionLogCreate,
    App1InteractionLogRead,
    App1LlmPromptRequest, # Import new request schema
    App1LlmResponse     # Import new response schema
)


# Dependency function to get the App1 service instance
def get_app1_service(session: AsyncSession = Depends(get_session)) -> App1Service:
    return App1Service(session=session)


router = APIRouter()

# --- Endpoint for Logging App1 Interactions ---
@router.post(
    "/log/{session_uuid}", # Path relative to the /app1 prefix
    response_model=App1InteractionLogRead,
    status_code=status.HTTP_201_CREATED,
    tags=["App1"],
    summary="Log a Single App1 Interaction Event"
)
async def log_app1_interaction_event(
    session_uuid: uuid.UUID,
    log_data: App1InteractionLogCreate,
    service: App1Service = Depends(get_app1_service)
):
    """
    Receives and stores a single App1 interaction event (e.g., user prompt, LLM response)
    associated with a specific session.
    """
    try:
        created_log = await service.log_app1_interaction(
            session_uuid=session_uuid,
            log_data=log_data
        )
        return created_log
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(e))
    except Exception as e:
        print(f"Error logging App1 interaction for session {session_uuid}: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"An unexpected error occurred while logging the App1 interaction: {e}"
        )


# --- Endpoint for App1 LLM Interaction ---
@router.post(
    "/llm/{session_uuid}", # Path relative to the /app1 prefix
    response_model=App1LlmResponse,
    tags=["App1"],
    summary="Send prompt to App1 LLM (Groq)"
)
async def get_app1_llm_response_endpoint(
    session_uuid: uuid.UUID,
    prompt_data: App1LlmPromptRequest, # Expects {"prompt": "user text"} in body
    service: App1Service = Depends(get_app1_service)
):
    """
    Receives a user prompt, sends it to the configured Groq LLM via the App1Service,
    logs the interaction internally via the service, and returns the LLM's response.
    """
    try:
        # Service method handles calling Groq and logging prompt/response/errors
        response_text = await service.get_llm_response(
            session_uuid=session_uuid,
            prompt=prompt_data.prompt
            # Can add model selection later if needed: model=prompt_data.model
        )
        # Return the response text structured according to the schema
        return App1LlmResponse(response_text=response_text)

    except ValueError as e:
        # Handle specific errors like missing API key
        raise HTTPException(status_code=status.HTTP_503_SERVICE_UNAVAILABLE, detail=str(e))
    except APIError as e:
         # Handle specific API errors from Groq (e.g., rate limits, server errors)
         print(f"Groq API Error for session {session_uuid}: Status {e.status_code} - {e.message}")
         raise HTTPException(status_code=status.HTTP_503_SERVICE_UNAVAILABLE, detail=f"LLM service error: {e.message}")
    except Exception as e:
        # Catch any other unexpected errors during the process
        print(f"Unexpected error in App1 LLM endpoint for session {session_uuid}: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"An unexpected error occurred while processing the LLM request."
        )

