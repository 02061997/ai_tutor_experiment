# backend/schemas/summary.py

# --- Existing Imports ---
from pydantic import BaseModel, Field, ConfigDict # Ensure BaseModel is imported
from typing import Optional, List, Dict, Union # Added List, Dict, Union

# --- Existing Schemas (if any) ---
class SummaryRequest(BaseModel):
    text_to_summarize: str

class SummaryResponse(BaseModel): # Keep or remove if fully replaced by structured
    summary_text: str

# --- NEW Schemas for Structured Summary ---
class StructuredSummarySection(BaseModel):
    """Represents one section of the structured summary."""
    title: str
    # Content can be a single string (for sections without sub-points)
    # or a dictionary (for sections with sub-points like Introduction)
    content: Union[str, Dict[str, str]]

    model_config = ConfigDict(from_attributes=True)


class StructuredSummaryResponse(BaseModel):
    """The overall response containing the list of summary sections."""
    summary: List[StructuredSummarySection]

    model_config = ConfigDict(from_attributes=True)
# --- END NEW SCHEMAS ---