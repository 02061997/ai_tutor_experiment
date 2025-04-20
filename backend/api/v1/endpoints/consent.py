# backend/api/v1/endpoints/consent.py
# Functional Version (Corrected Paths)

import uuid
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, status, Body, Query
from sqlmodel.ext.asyncio.session import AsyncSession

# Dependency for DB session
from backend.db.database import get_session

# Service and Schemas
from backend.services.consent_service import ConsentService
from backend.schemas.consent import ConsentCreate, ConsentRead
from backend.db.models import Consent # Import model for response_model mapping


# Dependency function to get the service instance
def get_consent_service(session: AsyncSession = Depends(get_session)) -> ConsentService:
    return ConsentService(session=session)

router = APIRouter()

@router.post(
    "/session", # Correct path
    response_model=ConsentRead,
    status_code=status.HTTP_201_CREATED,
    tags=["Consent & Session"],
    summary="Create a new Participant and Consent Session"
)
async def create_new_session(
    consent_data: ConsentCreate,
    service: ConsentService = Depends(get_consent_service)
):
    """
    Initiates a new participant session:
    - Creates a new anonymous Participant record.
    - Creates a Consent record associated with the participant.
    - Randomly assigns the participant to App1/App2 and Paper1/Paper2.
    - Stores initial demographics and baseline data provided.

    Args:
        consent_data (ConsentCreate): Demographics and baseline info.

    Returns:
        ConsentRead: Details of the created session, including assigned app/paper and UUIDs.
    """
    try:
        new_consent_session = await service.create_consent_session(consent_data=consent_data)
        return new_consent_session # Simply return the SQLModel instance
    except Exception as e:
        # Log the exception e
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to create session: {e}"
        )

@router.get(
    "/session/{session_uuid}", # Corrected path
    response_model=ConsentRead,
    tags=["Consent & Session"],
    summary="Get Session Details by UUID"
)
async def get_session_details(
    session_uuid: uuid.UUID,
    service: ConsentService = Depends(get_consent_service)
):
    """
    Retrieves the details for a specific consent session.
    """
    consent_session = await service.get_consent_session(session_uuid=session_uuid)
    if not consent_session:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Session with UUID {session_uuid} not found."
        )
    return ConsentRead.model_validate(consent_session)


@router.post(
    "/session/{session_uuid}/agree", # Corrected path
    response_model=ConsentRead,
    tags=["Consent & Session"],
    summary="Record Consent Agreement"
)
async def record_agreement(
    session_uuid: uuid.UUID,
    service: ConsentService = Depends(get_consent_service)
):
    """
    Marks a session as having consent agreed upon by the participant.
    Records the timestamp of agreement.
    """
    updated_session = await service.record_consent_agreement(session_uuid=session_uuid)
    if not updated_session:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Session with UUID {session_uuid} not found."
        )
    return ConsentRead.model_validate(updated_session)

@router.post(
    "/session/{session_uuid}/start", # Corrected path
    response_model=ConsentRead,
    tags=["Consent & Session"],
    summary="Record Start of Main Task"
)
async def record_task_start(
    session_uuid: uuid.UUID,
    service: ConsentService = Depends(get_consent_service)
):
    """
    Records the timestamp when the participant starts the main experiment task (App1 or App2).
    """
    updated_session = await service.start_session_task(session_uuid=session_uuid)
    if not updated_session:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Session with UUID {session_uuid} not found."
        )
    return ConsentRead.model_validate(updated_session)

@router.post(
    "/session/{session_uuid}/end", # Corrected path
    response_model=ConsentRead,
    tags=["Consent & Session"],
    summary="Record End of Session"
)
async def record_session_end(
    session_uuid: uuid.UUID,
    status_query: str = Query(..., alias="status", description="Final status ('Completed', 'Abandoned', 'Error')"),
    service: ConsentService = Depends(get_consent_service)
):
    """
    Records the end timestamp and final status for the session.
    """
    if status_query not in ['Completed', 'Abandoned', 'Error']:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid status value. Must be 'Completed', 'Abandoned', or 'Error'."
        )

    updated_session = await service.end_session(session_uuid=session_uuid, status=status_query)
    if not updated_session:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Session with UUID {session_uuid} not found."
        )
    return ConsentRead.model_validate(updated_session)