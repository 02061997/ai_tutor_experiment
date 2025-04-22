# backend/api/v1/endpoints/app2.py

import uuid
import os
from typing import List, Optional, Dict, Union
# --- Add uuid to imports if not already there ---
from pydantic import BaseModel # Keep BaseModel if needed for schemas defined here
from fastapi import APIRouter, Depends, HTTPException, status
from sqlmodel.ext.asyncio.session import AsyncSession
from sqlmodel import select

# Dependencies and Schemas
from backend.db.database import get_session
from backend.db.models import Consent
from backend.services.app2_service import App2Service
# --- Import Schemas ---
from backend.schemas.summary import StructuredSummaryResponse # Import the response schema
# --------------------
from backend.core.config import settings
from backend.rag.retriever import extract_text_from_pdf

# Dependency function (remains the same)
def get_app2_service() -> App2Service:
    return App2Service()

# Paper Mapping (Ensure Paper2 is added if needed!)
PAPER_FILE_MAP = {
    "Paper1": "./static/pdfs/chapter1.pdf",
    "Paper2": "./static/pdfs/chapter2.pdf", #<-- ### ADD MAPPING FOR PAPER 2 ###
    # Make sure 'chapter2.pdf' (or the correct filename) exists in static/pdfs
}

router = APIRouter()

# --- CORRECTED Endpoint Definition ---
@router.get(
    "/summary/{session_id}", # Changed path parameter name
    response_model=StructuredSummaryResponse,
    status_code=status.HTTP_200_OK,
    tags=["App2"],
    summary="Generate Structured AI Summary for Participant's Assigned Paper"
)
async def generate_participant_paper_summary(
        session_id: uuid.UUID, # Parameter name matches path
        db: AsyncSession = Depends(get_session),
        service: App2Service = Depends(get_app2_service)
):
    """
    Retrieves the paper assigned to the participant (via session ID),
    and uses the App2Service to generate a STRUCTURED summary.
    """
    try:
        # 1. Find the consent record using SESSION ID
        # --- UPDATED QUERY ---
        consent_statement = select(Consent).where(Consent.session_uuid == session_id)
        # -------------------
        consent_result = await db.exec(consent_statement)
        consent_record = consent_result.first()

        # Check if record found (This check remains valid)
        if not consent_record:
            # Use session_id in error message
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=f"Session not found for ID: {session_id}")
        if not consent_record.assigned_paper:
            # This case might indicate an issue during consent saving
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=f"Session {session_id} has no assigned paper.")

        # 2. Map assigned paper ID to file path
        paper_key = consent_record.assigned_paper # e.g., "Paper1" or "Paper2"
        pdf_path = PAPER_FILE_MAP.get(paper_key)
        if not pdf_path or not os.path.exists(pdf_path):
            print(f"ERROR: PDF file path not found or invalid for paper key '{paper_key}'. Looked for path: {pdf_path}")
            raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=f"Configuration error: PDF file for '{paper_key}' not found on server.")

        # 3. Call the service method with the paper_id (e.g., "Paper1")
        print(f"DEBUG: Calling App2Service.generate_structured_summary for session {session_id}, paper {paper_key}")
        structured_summary_list = await service.generate_structured_summary(
            paper_id=paper_key
        )

        # 4. Return the structured summary
        return StructuredSummaryResponse(summary=structured_summary_list)

    # ... (Error handling remains the same) ...
    except FileNotFoundError as e:
        print(f"Error processing summary (FileNotFound likely from vector store): {e}")
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=f"Server error: Could not find paper data.")
    except ValueError as e:
        print(f"Error generating summary (ValueError): {e}")
        if "client is not configured" in str(e) or "Gemini model unavailable" in str(e) or "vector store for paper" in str(e):
            # Include vector store not found as potentially recoverable/config issue
            raise HTTPException(status_code=status.HTTP_503_SERVICE_UNAVAILABLE, detail=str(e))
        else:
            raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=f"Data processing error: {e}")
    except HTTPException as e:
        raise e
    except Exception as e:
        print(f"Unexpected error generating summary for session {session_id}: {e}")
        import traceback
        traceback.print_exc()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"An unexpected server error occurred while generating the summary."
        )