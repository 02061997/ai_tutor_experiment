# backend/api/v1/endpoints/quiz.py

import uuid
import logging
import traceback # Keep for logging if needed
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, status, Body

# Dependencies and Schemas
from backend.api.deps import get_llm_quiz_service # Dependency getter for the service
from backend.schemas.quiz import ( # Import the correct schemas
    GeneratedMCQForParticipant,
    GeneratedMCQAnswerInput,
    GeneratedMCQAnswerFeedback
)
from backend.services.llm_quiz_service import LLMQuizService # Import the service class

logger = logging.getLogger(__name__)
router = APIRouter()


@router.post(
    "/next/{session_uuid}",
    response_model=GeneratedMCQForParticipant, # Response model matches service return
    tags=["LLM Quiz"],
    summary="Get Next LLM-Generated Quiz Question",
    description="Gets the next appropriate MCQ for the participant's session. Returns a question or a completion/error status."
)
async def get_next_llm_question( # Renamed function for clarity
        session_uuid: uuid.UUID,
        service: LLMQuizService = Depends(get_llm_quiz_service) # Inject the service
):
    """
    Gets the next appropriate MCQ for the participant's session using the LLMQuizService.
    Handles potential errors gracefully by returning them within the defined schema.
    """
    try:
        logger.info(f"Request received for next LLM question for session {session_uuid}")
        # --- Call the CORRECT service method name ---
        # Pass session_uuid to the service method, which expects session_id
        next_question_response = await service.get_next_question(session_id=session_uuid)
        # -----------------------------------------

        # The service method should now always return a valid schema object
        if not next_question_response:
            # This case indicates an unexpected issue within the service if it returns None
            logger.error(f"Service returned None unexpectedly for session {session_uuid}")
            # Return a valid schema indicating an error state
            return GeneratedMCQForParticipant(quiz_complete=True, error="Internal error fetching question state.")

        # Log details before returning
        log_mcq_id = getattr(next_question_response, 'mcq_id', 'N/A') # Safely get mcq_id
        log_complete = getattr(next_question_response, 'quiz_complete', 'N/A')
        log_error = getattr(next_question_response, 'error', None)
        logger.info(f"Returning next question state for session {session_uuid}: MCQ ID={log_mcq_id}, Complete={log_complete}, Error='{log_error}'")

        return next_question_response # Return the schema object received from the service

    except Exception as e: # Catch any truly unexpected errors not handled by the service
        logger.exception(f"Unhandled exception in /quiz/next endpoint for session {session_uuid}: {e}")
        # Raise a generic 500 error - avoid returning schema here as it might fail validation
        # if the exception occurred before the service call completed.
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="An unexpected server error occurred while fetching the next question."
        )


@router.post(
    "/answer_llm/{session_uuid}", # Use the distinct path
    response_model=GeneratedMCQAnswerFeedback, # Response model matches service return
    tags=["LLM Quiz"],
    summary="Submit Answer for LLM-Generated MCQ",
    description="Processes the participant's answer, records attempt, returns feedback."
)
async def submit_llm_answer( # Renamed function for clarity
        session_uuid: uuid.UUID,
        answer_data: GeneratedMCQAnswerInput = Body(...), # Use correct input schema from request Body
        service: LLMQuizService = Depends(get_llm_quiz_service) # Inject the service
):
    """
    Processes the participant's answer using the LLMQuizService.
    """
    try:
        logger.info(f"Processing answer for session {session_uuid}, mcq {answer_data.mcq_id}, chosen letter {answer_data.chosen_answer_letter}")
        # --- Call the CORRECT service method name ---
        feedback = await service.submit_answer(
            session_id=session_uuid, # Pass session_id
            request_data=answer_data     # Pass the validated input schema object
        )
        # ------------------------------------------
        logger.info(f"Answer processed for session {session_uuid}, mcq {answer_data.mcq_id}. Correct: {feedback.is_correct}, QuizComplete: {feedback.quiz_complete}")
        return feedback # Return the feedback schema object from the service

    except ValueError as e: # Catch specific logical errors raised by the service
        logger.warning(f"ValueError processing answer for session {session_uuid}, mcq {answer_data.mcq_id}: {e}")
        # Determine appropriate HTTP status based on the error
        if "not found" in str(e).lower(): # e.g., "Session not found", "Question not found"
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(e))
        else: # Other value errors likely indicate bad input
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))
    except RuntimeError as e: # Catch internal service runtime errors (e.g., DB issue, unexpected LLM state)
        logger.error(f"Runtime error processing answer for session {session_uuid}, mcq {answer_data.mcq_id}: {e}", exc_info=True) # Log traceback
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=str(e))
    except Exception as e: # Catch any other unexpected error
        logger.exception(f"Unexpected error processing answer for session {session_uuid}, mcq {answer_data.mcq_id}: {e}") # Log traceback
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to process answer due to an unexpected server error."
        )