# backend/schemas/dashboard.py

from pydantic import BaseModel, Field
from typing import List, Dict, Optional, Any, Union
import uuid

# --- Schema for GET /dashboard/summary ---
class SummaryStats(BaseModel):
    """Aggregated summary statistics for the experiment."""
    total_participants: int = Field(..., description="Total number of participants who started a session")
    completed_participants: int = Field(..., description="Number of participants who completed the session")
    abandoned_participants: int = Field(..., description="Number of participants who abandoned the session")
    error_participants: int = Field(..., description="Number of sessions ending in an error state")
    assigned_app1_count: int = Field(..., description="Number of participants assigned to App1")
    assigned_app2_count: int = Field(..., description="Number of participants assigned to App2")
    completion_rate: float = Field(..., ge=0, le=100, description="Overall completion percentage")

# --- Schema for GET /dashboard/survey/results ---
class AggregatedSurveyResult(BaseModel):
    """Aggregated results for a specific survey question."""
    survey_type: str = Field(..., description="The type of survey analyzed")
    question_key: str = Field(..., description="The key identifying the question analyzed")
    total_responses_for_question: int = Field(..., description="Number of sessions that included a response to this question")
    response_counts: Dict[str, int] = Field(..., description="Counts for each unique answer option provided")

# --- Schema for GET /dashboard/quiz/performance ---
class ThetaDistribution(BaseModel):
    """Histogram data for theta distribution."""
    counts: List[int] = Field(..., description="Counts per bin")
    bin_edges: List[float] = Field(..., description="Edges of the histogram bins")

class AggregatedQuizPerformance(BaseModel):
    """Aggregated performance metrics from completed quizzes."""
    total_completed_attempts: int = Field(..., description="Number of quiz attempts included in the aggregation")
    average_final_theta: Optional[float] = Field(default=None, description="Average estimated ability (theta) at the end of completed quizzes")
    median_final_theta: Optional[float] = Field(default=None, description="Median estimated ability (theta) at the end of completed quizzes")
    average_final_se: Optional[float] = Field(default=None, description="Average standard error (SE) of the theta estimate at the end of completed quizzes")
    average_items_administered: Optional[float] = Field(default=None, description="Average number of items administered in completed quizzes")
    theta_distribution: Optional[ThetaDistribution] = Field(default=None, description="Histogram data representing the distribution of final theta scores")

# --- Schema for GET /dashboard/quiz/item_analysis/{question_id} ---
class AggregatedItemAnalysis(BaseModel):
    """Aggregated statistics for a specific quiz item."""
    question_id: str = Field(..., description="UUID of the question analyzed")
    total_administrations: int = Field(..., description="Number of times this item was administered in completed quizzes")
    correct_response_count: int = Field(..., description="Number of times this item was answered correctly")
    p_value: Optional[float] = Field(default=None, description="Item difficulty (proportion correct). Lower is harder.")
    # point_biserial: Optional[float] = Field(default=None, description="Item discrimination (correlation with total score/theta)") # Add if calculated
    message: Optional[str] = Field(default=None, description="Notes about the analysis (e.g., simplifications)")

# --- Schema for GET /dashboard/interactions/heatmap ---
class HeatmapDataPoint(BaseModel):
    """Represents a single point with intensity for heatmap.js."""
    x: Union[int, float] = Field(..., description="X-coordinate relative to the target element")
    y: Union[int, float] = Field(..., description="Y-coordinate relative to the target element")
    value: Union[int, float] = Field(..., description="Intensity value at this coordinate (e.g., click count, dwell time)")

class AggregatedHeatmap(BaseModel):
    """Aggregated heatmap data for a target element."""
    target: str = Field(..., description="Identifier of the HTML element analyzed")
    heatmap_data: List[HeatmapDataPoint] = Field(..., description="List of data points for heatmap generation")
    aggregation_method: Optional[str] = Field(default=None, description="Description of how data was aggregated (e.g., 'simple_coordinate_count', 'grid_cell_count')")

# --- Schema for GET /dashboard/interactions/pdf ---
class PdfTopSelection(BaseModel):
    """Represents aggregated count for a specific text selection."""
    text: str
    count: int

class AggregatedPdfInteractionData(BaseModel):
    """Aggregated interaction statistics for a specific PDF document."""
    pdf_url: str = Field(..., description="URL or identifier of the PDF analyzed")
    total_interactions_logged: int = Field(..., description="Total number of interaction logs recorded for this PDF")
    event_type_counts: Dict[str, int] = Field(..., description="Counts of different interaction event types ('pdf_page_view', 'pdf_scroll', etc.)")
    # Placeholder fields - require complex aggregation logic in the service
    avg_time_per_page: Optional[Dict[str, float]] = Field(default=None, description="Average time spent per page number (e.g., {'1': 30.5, '2': 45.2})")
    scroll_depth_histogram: Optional[Dict[str, Any]] = Field(default=None, description="Histogram data for maximum scroll depth reached per session/page")
    zoom_actions_count: Optional[int] = Field(default=None, description="Total count of zoom events recorded")
    top_text_selections: Optional[List[PdfTopSelection]] = Field(default=None, description="Most frequently selected text snippets and their counts")
    message: Optional[str] = Field(default=None, description="Notes about the analysis (e.g., simplifications)")