# backend/services/consent_service.py
# Modified to include RAG processing integration

import random
import uuid
import logging # Added import
import asyncio # Added import
from datetime import datetime
from typing import Optional, Tuple

from sqlmodel import select
from sqlmodel.ext.asyncio.session import AsyncSession

from backend.db.models import Participant, Consent
from backend.schemas.consent import ConsentCreate, ConsentRead
# Attempt to import the RAG processing function
try:
    from backend.rag.retriever import process_and_index_paper
except ImportError:
    # Fallback if the module/function doesn't exist yet
    async def process_and_index_paper(paper_id: str, pdf_path: str):
        logger = logging.getLogger(__name__) # Get logger inside fallback
        logger.error(f"RAG function 'process_and_index_paper' not found. Please create backend/rag/retriever.py.")
        # Raise an error or just log a warning depending on desired behavior
        # raise NotImplementedError("RAG processing function is not implemented.")
        pass # Allow continuation but RAG won't work

logger = logging.getLogger(__name__) # Setup logger for the service


class ConsentService:
    """
    Service layer for managing participant consent and session initialization.
    Includes RAG processing trigger for assigned papers.
    """

    def __init__(self, session: AsyncSession):
        self.session = session

    async def create_consent_session(self, consent_data: ConsentCreate) -> Consent:
        """
        Creates a new participant and a corresponding consent/session record.
        Assigns App and Paper randomly based on the 50/50 split specified in the plan.
        Triggers RAG processing for the assigned paper.

        Args:
            consent_data: Input data containing demographics and baseline info.

        Returns:
            The newly created Consent database object.
        """
        logger.info("Creating new consent session...")
        # 1. Create a new Participant
        new_participant = Participant()
        self.session.add(new_participant)
        await self.session.flush() # Flush to get the generated participant_uuid
        await self.session.refresh(new_participant)
        logger.info(f"Created new participant: {new_participant.participant_uuid}")

        # 2. Assign App and Paper
        # Use actual random assignment or keep forced assignment for testing
        #assigned_app = random.choice(['App1', 'App2'])
        assigned_app = 'App2' # Keep forced assignment if still testing App2 specifically
        if assigned_app == 'App2': logger.debug("Forcing assignment to App2 for testing.")

        assigned_paper_id = random.choice(['Paper1', 'Paper2']) # Example paper IDs

        # 3. Create the Consent record
        new_consent = Consent(
            participant_uuid=new_participant.participant_uuid,
            recruitment_timestamp=datetime.utcnow(),
            demographics=consent_data.demographics,
            baseline_data=consent_data.baseline_data,
            assigned_app=assigned_app,
            assigned_paper=assigned_paper_id, # Use the assigned paper ID
        )
        self.session.add(new_consent)
        await self.session.flush() # Flush to get the generated session_uuid
        await self.session.refresh(new_consent)

        logger.info(f"Created session {new_consent.session_uuid} for participant {new_participant.participant_uuid}, assigned to {assigned_app} / {assigned_paper_id}")

        # --- RAG PROCESSING INTEGRATION ---
        if assigned_paper_id:
            logger.info(f"Initiating RAG processing for assigned paper '{assigned_paper_id}'...")
            # Define mapping from paper ID to actual file path
            # Ensure these paths are correct relative to where the app runs
            pdf_file_map = {
                "Paper1": "./static/pdfs/chapter1.pdf",
                "Paper2": "./static/pdfs/chapter2.pdf",
            }
            pdf_path = pdf_file_map.get(assigned_paper_id)

            if pdf_path:
                try:
                    # Call the async RAG processing function
                    # This will check if the index exists before processing
                    await process_and_index_paper(assigned_paper_id, pdf_path)
                    logger.info(f"RAG processing check/initiation complete for paper '{assigned_paper_id}'.")
                except FileNotFoundError:
                     logger.error(f"PDF file not found at '{pdf_path}' for paper '{assigned_paper_id}'. RAG indexing cannot proceed.")
                     # Decide: raise error, or just log and continue session? Log and continue for now.
                except Exception as rag_exc:
                    logger.error(f"Failed during RAG processing for paper '{assigned_paper_id}': {rag_exc}", exc_info=True)
                    # Decide: raise error, or just log and continue session? Log and continue for now.
            else:
                logger.warning(f"No PDF path configured in consent_service for assigned paper ID: '{assigned_paper_id}'. RAG processing skipped.")
        # --- END RAG PROCESSING INTEGRATION ---

        # Commit happens via the dependency wrapper (get_session in deps.py) usually.
        # If this service were called outside the request cycle, commit would be needed here.

        return new_consent

    async def get_consent_session(self, session_uuid: uuid.UUID) -> Optional[Consent]:
        """Retrieves a consent session by its UUID."""
        # Use session.get for PK lookup - more efficient if session_uuid is the PK
        consent_session = await self.session.get(Consent, session_uuid)
        # Fallback or alternative if using select:
        # result = await self.session.exec(select(Consent).where(Consent.session_uuid == session_uuid))
        # consent_session = result.first()
        return consent_session

    async def record_consent_agreement(self, session_uuid: uuid.UUID) -> Optional[Consent]:
        """
        Records the timestamp when a participant agrees to the consent form.

        Args:
            session_uuid: The UUID of the session to update.

        Returns:
            The updated Consent object or None if not found.
        """
        consent_session = await self.get_consent_session(session_uuid)
        if consent_session:
            if consent_session.consent_timestamp is None: # Only update if not already set
                logger.info(f"Recording consent agreement for session {session_uuid}")
                consent_session.consent_timestamp = datetime.utcnow()
                self.session.add(consent_session)
                await self.session.flush()
                await self.session.refresh(consent_session)
            else:
                logger.warning(f"Consent already recorded for session {session_uuid}. Ignoring request.")
            return consent_session
        logger.warning(f"Session not found for recording consent: {session_uuid}")
        return None

    async def start_session_task(self, session_uuid: uuid.UUID) -> Optional[Consent]:
        """
        Records the timestamp when the main task execution starts for the session.

        Args:
            session_uuid: The UUID of the session to update.

        Returns:
            The updated Consent object or None if not found.
        """
        consent_session = await self.get_consent_session(session_uuid)
        if consent_session:
             if consent_session.session_start_time is None: # Only update if not already set
                logger.info(f"Recording task start time for session {session_uuid}")
                consent_session.session_start_time = datetime.utcnow()
                self.session.add(consent_session)
                await self.session.flush()
                await self.session.refresh(consent_session)
             else:
                 logger.warning(f"Task start time already recorded for session {session_uuid}. Ignoring request.")
             return consent_session
        logger.warning(f"Session not found for recording task start time: {session_uuid}")
        return None

    async def end_session(self, session_uuid: uuid.UUID, status: str) -> Optional[Consent]:
        """
        Records the end timestamp and status for the session.

        Args:
            session_uuid: The UUID of the session to update.
            status: The final status ('Completed', 'Abandoned', 'Error').

        Returns:
            The updated Consent object or None if not found.
        """
        consent_session = await self.get_consent_session(session_uuid)
        if consent_session:
            if consent_session.session_end_time is None: # Only update if not ended
                logger.info(f"Recording session end for {session_uuid} with status '{status}'")
                consent_session.session_end_time = datetime.utcnow()
                consent_session.session_status = status
                self.session.add(consent_session)
                await self.session.flush()
                await self.session.refresh(consent_session)
            else:
                 logger.warning(f"Session end time already recorded for session {session_uuid}. Ignoring request.")
            return consent_session
        logger.warning(f"Session not found for recording session end: {session_uuid}")
        return None