# backend/services/test_service.py

import uuid
from datetime import datetime
from typing import List, Optional

from sqlmodel import select
from sqlmodel.ext.asyncio.session import AsyncSession

# Import models and schemas
from backend.db.models import FinalTestResponse, Consent
from backend.schemas.test import FinalTestSubmission, FinalTestResponseCreate


class TestService:
    """
    Service layer for handling Final Test submissions.
    """

    def __init__(self, session: AsyncSession):
        self.session = session

    async def record_final_test(
        self,
        session_uuid: uuid.UUID,
        submission: FinalTestSubmission
    ) -> List[FinalTestResponse]:
        """
        Records all answers submitted as part of a final test for a session.

        Args:
            session_uuid: The UUID of the session the test belongs to.
            submission: The schema containing the list of answers.

        Returns:
            A list of the created FinalTestResponse database objects.

        Raises:
            ValueError: If the associated session_uuid does not exist.
        """
        # 1. Verify session_uuid exists (optional but recommended)
        consent_check = await self.session.get(Consent, session_uuid)
        if not consent_check:
             raise ValueError(f"Session with UUID {session_uuid} not found.")

        # 2. Prepare database objects for all answers
        db_responses: List[FinalTestResponse] = []
        submission_timestamp = datetime.utcnow() # Consistent timestamp for all answers in batch

        for answer_data in submission.answers:
            # Create DB model instance from the schema data
            # Note: is_correct is left as None by default in the model
            db_response = FinalTestResponse(
                session_uuid=session_uuid,
                question_id=answer_data.question_id,
                user_answer=answer_data.user_answer,
                time_per_question_ms=answer_data.time_per_question_ms,
                answer_timestamp=submission_timestamp # Use batch timestamp
                # response_id is generated automatically
            )
            db_responses.append(db_response)

        # 3. Add all response objects to the session and save
        self.session.add_all(db_responses)
        await self.session.flush() # Persist to get IDs etc.

        # Refresh objects to get database-generated values (like response_id)
        for resp in db_responses:
            await self.session.refresh(resp)

        print(f"Recorded {len(db_responses)} final test answers for session {session_uuid}")

        # 4. Return the created database objects
        return db_responses