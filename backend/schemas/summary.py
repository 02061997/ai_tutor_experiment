# backend/schemas/summary.py

from pydantic import BaseModel, Field
from typing import Optional

# --- Schemas for App2 Summary Generation ---

class SummaryRequest(BaseModel):
    """
    Schema for the request body sent to the summary generation endpoint.
    """
    text_to_summarize: str = Field(..., description="The text content that needs to be summarized.")
    # Optional: Could add parameters like desired length, focus points, etc.
    # max_length: Optional[int] = None

class SummaryResponse(BaseModel):
    """
    Schema for the response body returned by the summary generation endpoint.
    """
    summary_text: str = Field(..., description="The AI-generated summary text.")

