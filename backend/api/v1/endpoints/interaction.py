# backend/api/v1/endpoints/interaction.py
# Corrected Version (Path prefixes removed)

import uuid
from typing import List

from fastapi import APIRouter, Depends, HTTPException, status, Body
from sqlmodel.ext.asyncio.session import AsyncSession

# Dependency for DB session
from backend.db.database import get_session

# Service and Schemas
from backend.services.interaction_service import InteractionService
from backend.schemas.interaction import InteractionLogCreateBatch, InteractionLogRead
from backend.db.models import InteractionLog # Import model for response_model mapping


# Dependency function to get the service instance
def get_interaction_service(session: AsyncSession = Depends(get_session)) -> InteractionService:
    return InteractionService(session=session)

router = APIRouter()

@router.post(
    "/log/{session_uuid}", # Corrected path
    status_code=status.HTTP_201_CREATED, # Use 201 Created or 202 Accepted for batch posts
    tags=["Interaction"],
    summary="Log a Batch of User Interactions for a Session"
)
async def log_interaction_batch_for_session(
    session_uuid: uuid.UUID,
    batch_data: InteractionLogCreateBatch,
    service: InteractionService = Depends(get_interaction_service)
):
    """
    Receives and stores a batch of user interaction logs (clicks, scrolls,
    PDF events, etc.) associated with a specific session.

    The frontend should batch these interactions to reduce network requests.

    Args:
        session_uuid (uuid.UUID): The session identifier from the URL path.
        batch_data (InteractionLogCreateBatch): A list of interaction log entries.

    Returns:
        JSON message confirming the number of logs received.

    Raises:
        HTTPException 404: If the session_uuid is not found.
        HTTPException 500: For other server errors.
    """
    try:
        processed_count = await service.log_interactions_batch(
            session_uuid=session_uuid,
            batch_data=batch_data
        )
        return {"message": f"Received {processed_count} interaction logs."}
    except ValueError as e:
        # Catch specific error from service if session not found
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(e) # e.g., "Session with UUID ... not found."
        )
    except Exception as e:
        # Log the exception e
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to log interactions: {e}"
        )

@router.get(
    "/logs/session/{session_uuid}", # Corrected path
    response_model=List[InteractionLogRead],
    tags=["Interaction"],
    summary="Get All Interaction Logs for a Session"
)
async def get_all_interaction_logs_for_session(
    session_uuid: uuid.UUID,
    service: InteractionService = Depends(get_interaction_service)
):
    """
    Retrieves all interaction logs associated with a specific session UUID,
    ordered chronologically.
    (Primarily for debugging or admin purposes).
    """
    logs = await service.get_interactions_for_session(session_uuid=session_uuid)
    # Validate each log object against the schema
    # Use model_validate for Pydantic V2
    return [InteractionLogRead.model_validate(log) for log in logs]