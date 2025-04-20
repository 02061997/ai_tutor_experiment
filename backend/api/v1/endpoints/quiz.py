# backend/api/v1/endpoints/quiz.py
# Corrected Version (Path prefixes removed)

import uuid
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, status, Query, Body
from sqlmodel.ext.asyncio.session import AsyncSession
from pydantic import BaseModel # Import BaseModel for new response schema

# Dependency for DB session
from backend.db.database import get_session

# Service and Schemas
from backend.services.adaptive_quiz_service import AdaptiveQuizService
from backend.schemas.quiz import (
    QuizAnswerInput,
    QuizNextQuestionResponse,
    QuizQuestionForParticipant # Used in response schemas
)
# Models might be needed if service returns them directly sometimes
# from backend.db.models import QuizAttemptState

# Dependency function to get the service instance
def get_adaptive_quiz_service(session: AsyncSession = Depends(get_session)) -> AdaptiveQuizService:
    # Initialize service; could potentially inject CAT params from config here
    return AdaptiveQuizService(session=session)

# --- Define Response Schema for Starting Quiz ---
class QuizStartResponse(BaseModel):
    """
    Response model when starting a quiz, includes the attempt ID and the first question.
    """
    attempt_id: uuid.UUID
    first_question: QuizQuestionForParticipant


router = APIRouter()

@router.post(
    "/start/{session_uuid}", # Corrected path
    response_model=QuizStartResponse,
    status_code=status.HTTP_201_CREATED,
    tags=["Quiz"],
    summary="Start a New Adaptive Quiz Attempt"
)
async def start_new_quiz(
    session_uuid: uuid.UUID,
    quiz_id: Optional[str] = Query(None, description="Optional identifier if multiple quizzes exist"),
    service: AdaptiveQuizService = Depends(get_adaptive_quiz_service)
):
    """
    Initializes a new adaptive quiz attempt for the given session.
    - Selects the first question based on initial ability estimate.
    - Creates and stores the initial state for the quiz attempt.

    Args:
        session_uuid (uuid.UUID): The session identifier from the URL path.
        quiz_id (Optional[str]): Optional identifier for a specific quiz item bank.

    Returns:
        QuizStartResponse: Contains the unique `attempt_id` for this quiz attempt
                           and the details of the `first_question` to be presented.

    Raises:
        HTTPException 404: If the session_uuid is not found (implicitly checked if needed by service).
        HTTPException 500: If no valid quiz questions are found or the first item cannot be selected.
    """
    try:
        # The service returns the DB state object and the first question schema
        attempt_state, first_question = await service.start_quiz(
            session_uuid=session_uuid,
            quiz_id=quiz_id
        )
        # Structure the response using the custom schema
        return QuizStartResponse(
            attempt_id=attempt_state.attempt_id,
            first_question=first_question
        )
    except ValueError as e:
        # Handle errors like no items, inability to select first item, or invalid session
         raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, # Or 404 if session not found was the cause
            detail=f"Failed to start quiz: {e}"
        )
    except Exception as e:
        # Log the exception e
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"An unexpected error occurred while starting the quiz: {e}"
        )


@router.post(
    "/answer/{attempt_id}", # Corrected path
    response_model=QuizNextQuestionResponse,
    tags=["Quiz"],
    summary="Submit an Answer and Get Next Question"
)
async def submit_answer_and_get_next(
    attempt_id: uuid.UUID,
    answer_data: QuizAnswerInput,
    service: AdaptiveQuizService = Depends(get_adaptive_quiz_service)
):
    """
    Processes the participant's answer to the current question:
    - Updates the quiz attempt state (response history, administered items).
    - Re-estimates the participant's ability (theta) and standard error (SE).
    - Checks stopping criteria (e.g., max items, min standard error).
    - Selects the next item based on the updated ability estimate if the quiz continues.

    Args:
        attempt_id (uuid.UUID): The unique identifier for this quiz attempt.
        answer_data (QuizAnswerInput): The submitted answer details (question_id, selected_option_index).

    Returns:
        QuizNextQuestionResponse: Contains the next question to present (if quiz is not complete),
                                  a flag indicating completion status, and potentially final results.

    Raises:
        HTTPException 404: If the attempt_id is not found.
        HTTPException 400: If the quiz attempt is already complete or input is invalid.
        HTTPException 500: For internal errors during estimation or item selection.
    """
    try:
        next_step_response = await service.process_answer(
            attempt_id=attempt_id,
            answer_input=answer_data
        )
        return next_step_response
    except ValueError as e:
         # Handle specific errors like attempt not found, already complete, invalid question
         if "not found" in str(e).lower():
             raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(e))
         else:
              raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))
    except RuntimeError as e:
         # Handle potentially more critical errors (e.g., item bank inconsistencies)
         raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=str(e))
    except Exception as e:
        # Log the exception e
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"An unexpected error occurred while processing the answer: {e}"
        )