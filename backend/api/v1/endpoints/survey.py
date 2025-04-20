# backend/api/v1/endpoints/survey.py
# Corrected Version (Path prefixes removed)

import uuid
from typing import List
from datetime import datetime

from fastapi import APIRouter, Depends, HTTPException, status, Body
from sqlmodel.ext.asyncio.session import AsyncSession

# Dependency for DB session
from backend.db.database import get_session

# Service and Schemas
from backend.services.survey_service import SurveyService
from backend.schemas.survey import SurveyResponseCreate, SurveyResponseRead
from backend.db.models import SurveyResponse # Import model for response_model mapping

# Dependency function to get the service instance
def get_survey_service(session: AsyncSession = Depends(get_session)) -> SurveyService:
    return SurveyService(session=session)

router = APIRouter()

@router.post(
    "/response/{session_uuid}", # Corrected path
    response_model=SurveyResponseRead,
    status_code=status.HTTP_201_CREATED,
    tags=["Survey"],
    summary="Submit Survey Responses for a Session"
)
async def submit_survey_response(
    session_uuid: uuid.UUID,
    survey_data: SurveyResponseCreate,
    service: SurveyService = Depends(get_survey_service)
):
    """
    Records survey responses (e.g., experience survey, exit survey)
    submitted by the participant for a given session.

    Args:
        session_uuid (uuid.UUID): The session identifier from the URL path.
        survey_data (SurveyResponseCreate): The survey type and responses dictionary.

    Returns:
        SurveyResponseRead: Details of the recorded survey response.

    Raises:
        HTTPException 404: If the session_uuid is not found.
        HTTPException 500: For other server errors.
    """
    try:
        start_time = datetime.utcnow()
        end_time = start_time # Assuming submission marks the end for this simple endpoint

        new_response = await service.record_survey_response(
            session_uuid=session_uuid,
            survey_data=survey_data,
            start_time=start_time,
            end_time=end_time
        )
        # Use model_validate for Pydantic V2 compatibility
        return SurveyResponseRead.model_validate(new_response)
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(e)
        )
    except Exception as e:
        # Log the exception e
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to record survey response: {e}"
        )

@router.get(
    "/response/{response_id}", # Corrected path
    response_model=SurveyResponseRead,
    tags=["Survey"],
    summary="Get Survey Response by ID"
)
async def get_survey_response_by_id(
    response_id: uuid.UUID,
    service: SurveyService = Depends(get_survey_service)
):
    """
    Retrieves a specific survey response by its unique ID.
    (Primarily for debugging or admin purposes, not typically called by participant frontend).
    """
    response = await service.get_survey_response(response_id=response_id)
    if not response:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Survey response with ID {response_id} not found."
        )
    return SurveyResponseRead.model_validate(response)

@router.get(
    "/responses/session/{session_uuid}", # Corrected path
    response_model=List[SurveyResponseRead],
    tags=["Survey"],
    summary="Get All Survey Responses for a Session"
)
async def get_all_survey_responses_for_session(
    session_uuid: uuid.UUID,
    service: SurveyService = Depends(get_survey_service)
):
    """
    Retrieves all survey responses associated with a specific session UUID.
    (Primarily for debugging or admin purposes).
    """
    responses = await service.get_survey_responses_for_session(session_uuid=session_uuid)
    # Validate each response object against the schema
    return [SurveyResponseRead.model_validate(resp) for resp in responses]