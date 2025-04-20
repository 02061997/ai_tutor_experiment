# backend/services/survey_service.py
# Corrected version with 'await' added before session.exec calls

import uuid
from datetime import datetime
from typing import Optional, List # Added List

from sqlmodel import select
from sqlmodel.ext.asyncio.session import AsyncSession

from backend.db.models import SurveyResponse, Consent
from backend.schemas.survey import SurveyResponseCreate

class SurveyService:
    """
    Service layer for handling survey responses.
    """

    def __init__(self, session: AsyncSession):
        """
        Initializes the service with an async database session.

        Args:
            session: The database session dependency.
        """
        self.session = session

    async def record_survey_response(
        self,
        session_uuid: uuid.UUID,
        survey_data: SurveyResponseCreate,
        start_time: Optional[datetime] = None, # Allow endpoint to pass start time
        end_time: Optional[datetime] = None    # Allow endpoint to pass end time
    ) -> SurveyResponse:
        """
        Creates a new SurveyResponse record associated with a session. [cite: 93, 97]

        Args:
            session_uuid: The UUID of the session this response belongs to.
            survey_data: Input data containing survey type and responses dictionary.
            start_time: Optional start time of the survey. Defaults to now if None.
            end_time: Optional end time of the survey.

        Returns:
            The newly created SurveyResponse database object.

        Raises:
            ValueError: If the associated session_uuid does not exist.
        """
        # Optional: Verify session_uuid exists in the Consent table
        # --- DB CALL: Needs await ---
        consent_result = await self.session.exec(
            select(Consent.session_uuid).where(Consent.session_uuid == session_uuid)
        ) # Corrected: Added await
        if not consent_result.first(): # Corrected: Check result
             raise ValueError(f"Session with UUID {session_uuid} not found.")
        # --- End DB Call ---

        # Create the SurveyResponse object
        new_response = SurveyResponse(
            session_uuid=session_uuid,
            survey_type=survey_data.survey_type,
            responses=survey_data.responses,
            start_time=start_time or datetime.utcnow(), # Use provided start time or now
            end_time=end_time # Can be None if submitted immediately or timed separately
        )

        self.session.add(new_response)
        # These were already correct
        await self.session.flush()
        await self.session.refresh(new_response)

        print(f"Recorded survey '{survey_data.survey_type}' for session {session_uuid}")

        return new_response

    async def get_survey_response(self, response_id: uuid.UUID) -> Optional[SurveyResponse]:
        """Retrieves a survey response by its UUID."""
        # --- DB CALL: Needs await ---
        statement = select(SurveyResponse).where(SurveyResponse.response_id == response_id)
        result = await self.session.exec(statement) # Corrected: Added await
        return result.first() # Corrected: Access result
        # --- End DB Call ---

    async def get_survey_responses_for_session(self, session_uuid: uuid.UUID) -> List[SurveyResponse]:
         """Retrieves all survey responses for a given session."""
         # --- DB CALL: Needs await ---
         statement = select(SurveyResponse).where(SurveyResponse.session_uuid == session_uuid)
         result = await self.session.exec(statement) # Corrected: Added await
         return result.all() # Corrected: Access result
         # --- End DB Call ---

