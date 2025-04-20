# backend/services/interaction_service.py
# Corrected version with 'await' added before session.exec calls

import uuid
from datetime import datetime
from typing import List

from sqlmodel import select
from sqlmodel.ext.asyncio.session import AsyncSession

from backend.db.models import InteractionLog, Consent
from backend.schemas.interaction import InteractionLogCreateBatch, InteractionLogCreate

class InteractionService:
    """
    Service layer for handling and storing App2 interaction logs (UI, PDF).
    """

    def __init__(self, session: AsyncSession):
        """
        Initializes the service with an async database session.

        Args:
            session: The database session dependency.
        """
        self.session = session

    async def log_interactions_batch(
        self,
        session_uuid: uuid.UUID,
        batch_data: InteractionLogCreateBatch
    ) -> int:
        """
        Logs a batch of interaction events associated with a specific session.

        Args:
            session_uuid: The UUID of the session these interactions belong to.
            batch_data: A schema containing a list of interaction log entries.

        Returns:
            The number of interaction logs successfully processed and added.

        Raises:
            ValueError: If the associated session_uuid does not exist.
        """
        # 1. Verify session_uuid exists
        # --- DB CALL: Needs await ---
        statement = select(Consent.session_uuid).where(Consent.session_uuid == session_uuid)
        # Corrected: Added await and result handling
        result = await self.session.exec(statement)
        if not result.first():
                raise ValueError(f"Session with UUID {session_uuid} not found.")
        # --- End DB Call ---

        # 2. Process the batch
        added_count = 0
        logs_to_add: List[InteractionLog] = []
        backend_timestamp = datetime.utcnow() # Consistent timestamp for batch

        for log_entry_data in batch_data.logs:
            # Prepare payload, potentially adding frontend timestamp
            payload = log_entry_data.payload or {}
            if log_entry_data.timestamp_frontend:
                payload["timestamp_frontend_iso"] = log_entry_data.timestamp_frontend.isoformat()

            log_entry_db = InteractionLog(
                session_uuid=session_uuid,
                timestamp=backend_timestamp,
                event_type=log_entry_data.event_type,
                target_element_id=log_entry_data.target_element_id,
                pdf_url=log_entry_data.pdf_url,
                payload=payload,
                element_width=log_entry_data.element_width,
                element_height=log_entry_data.element_height,
            )
            logs_to_add.append(log_entry_db)
            added_count += 1

        # 3. Add all logs to the session efficiently
        if logs_to_add:
            self.session.add_all(logs_to_add)
            # This flush was already correct
            await self.session.flush() # Persist changes

        print(f"Logged {added_count} interaction(s) for session {session_uuid}")
        return added_count

    async def get_interactions_for_session(self, session_uuid: uuid.UUID) -> List[InteractionLog]:
            """Retrieves all interaction logs for a given session."""
            # --- DB CALL: Needs await ---
            statement = (
                select(InteractionLog)
                .where(InteractionLog.session_uuid == session_uuid)
                .order_by(InteractionLog.timestamp) # Order chronologically
            )
            # Corrected: Added await and result handling
            result = await self.session.exec(statement)
            return result.all()
            # --- End DB Call ---

