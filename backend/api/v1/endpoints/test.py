# backend/api/v1/endpoints/test.py

import uuid
from typing import List

from fastapi import APIRouter, Depends, HTTPException, status
from sqlmodel.ext.asyncio.session import AsyncSession

# Dependency for DB session
from backend.db.database import get_session

# Service and Schemas
from backend.services.test_service import TestService # Assuming test_service.py exists
from backend.schemas.test import FinalTestSubmission, FinalTestResponseRead


# Dependency function to get the service instance
def get_test_service(session: AsyncSession = Depends(get_session)) -> TestService:
    return TestService(session=session)


router = APIRouter()

@router.post(
    "/submit/{session_uuid}", # Path relative to the prefix added in router.py
    response_model=List[FinalTestResponseRead],
    status_code=status.HTTP_201_CREATED,
    tags=["Test"],
    summary="Submit Final Test Responses for a Session"
)
async def submit_final_test(
    session_uuid: uuid.UUID,
    submission: FinalTestSubmission, # Expects a body matching {"answers": [{...}, ...]}
    service: TestService = Depends(get_test_service)
):
    """
    Receives and stores all the answers submitted for the final test
    associated with a specific session.

    Args:
        session_uuid (uuid.UUID): The session identifier from the URL path.
        submission (FinalTestSubmission): The submitted test answers.

    Returns:
        List[FinalTestResponseRead]: A list of the created response records.

    Raises:
        HTTPException 404: If the session_uuid is not found.
        HTTPException 500: For other server errors during processing.
    """
    try:
        created_responses = await service.record_final_test(
            session_uuid=session_uuid,
            submission=submission
        )
        # FastAPI automatically serializes the list of ORM objects
        # using the FinalTestResponseRead schema because of response_model
        return created_responses
    except ValueError as e:
        # Handle case where session_uuid is not found by the service
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(e) # e.g., "Session with UUID ... not found."
        )
    except Exception as e:
        # Log the exception e for debugging
        print(f"Error submitting final test for session {session_uuid}: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"An unexpected error occurred while submitting the final test: {e}"
        )