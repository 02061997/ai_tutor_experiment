# backend/api/v1/endpoints/dashboard.py
# Corrected Version (Path prefixes removed)

import uuid
from typing import List, Optional, Dict, Any

from fastapi import APIRouter, Depends, HTTPException, status, Query
from sqlmodel.ext.asyncio.session import AsyncSession

# Dependency for DB session
from backend.db.database import get_session

# Service
from backend.services.dashboard_service import DashboardService

# Security dependency (using refined version from deps.py)
from backend.api.deps import get_current_researcher
from backend.db.models import Researcher # Import Researcher for type hint

# Dependency function to get the dashboard service instance
def get_dashboard_service(session: AsyncSession = Depends(get_session)) -> DashboardService:
    return DashboardService(session=session)

router = APIRouter()

# Apply the refined authentication dependency to all dashboard routes
AuthDependency = Depends(get_current_researcher)

@router.get(
    "/summary", # Corrected path
    response_model=Dict[str, Any], # Replace with specific schema later if desired
    tags=["Dashboard"],
    summary="Get Overall Experiment Summary Statistics"
)
async def get_dashboard_summary(
    service: DashboardService = Depends(get_dashboard_service),
    current_researcher: Researcher = AuthDependency # Apply auth dependency
):
    """
    Retrieves aggregated summary statistics for the entire experiment,
    such as total participant counts and completion rates.
    (Requires researcher authentication).
    """
    try:
        summary = await service.get_experiment_summary()
        return summary
    except Exception as e:
        # Log the exception e
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to retrieve experiment summary: {e}"
        )

@router.get(
    "/survey/results", # Corrected path
    response_model=Dict[str, Any], # Replace with specific schema later if desired
    tags=["Dashboard"],
    summary="Get Aggregated Results for a Specific Survey Question"
)
async def get_dashboard_survey_results(
    survey_type: str = Query(..., description="Type of survey (e.g., 'experience_app1', 'exit')"),
    question_key: str = Query(..., description="Key identifying the question within the survey's responses JSON"),
    service: DashboardService = Depends(get_dashboard_service),
    current_researcher: Researcher = AuthDependency # Apply auth dependency
):
    """
    Retrieves aggregated results (e.g., counts per option) for a specific
    question within a specific survey type. Results are anonymized.
    (Requires researcher authentication).
    """
    try:
        results = await service.get_aggregated_survey_results(
            survey_type=survey_type,
            question_key=question_key
        )
        return results
    except Exception as e:
        # Log the exception e
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to retrieve aggregated survey results: {e}"
        )

@router.get(
    "/quiz/performance", # Corrected path
    response_model=Dict[str, Any], # Replace with specific schema later if desired
    tags=["Dashboard"],
    summary="Get Aggregated Quiz Performance Metrics"
)
async def get_dashboard_quiz_performance(
    service: DashboardService = Depends(get_dashboard_service),
    current_researcher: Researcher = AuthDependency # Apply auth dependency
):
    """
    Retrieves aggregated performance metrics from completed adaptive quiz attempts,
    such as average final ability (theta), SE, items administered, and distributions.
    Results are anonymized.
    (Requires researcher authentication).
    """
    try:
        performance_data = await service.get_aggregated_quiz_performance()
        return performance_data
    except Exception as e:
        # Log the exception e
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to retrieve aggregated quiz performance: {e}"
        )

@router.get(
    "/quiz/item_analysis/{question_id}", # Path unchanged (correct relative to prefix)
    response_model=Dict[str, Any], # Replace with specific schema later if desired
    tags=["Dashboard"],
    summary="Get Aggregated Analysis for a Specific Quiz Item"
)
async def get_dashboard_item_analysis(
    question_id: uuid.UUID,
    service: DashboardService = Depends(get_dashboard_service),
    current_researcher: Researcher = AuthDependency # Apply auth dependency
):
    """
    Retrieves aggregated statistics for a specific quiz item (identified by UUID),
    such as the number of times it was administered and its p-value (difficulty).
    Results are anonymized.
    (Requires researcher authentication).
    """
    try:
        analysis = await service.get_aggregated_item_analysis(question_id=question_id)
        if analysis.get("total_administrations", 0) == 0:
             pass # Return analysis indicating zero administrations
        return analysis
    except Exception as e:
        # Log the exception e
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to retrieve item analysis: {e}"
        )

@router.get(
    "/interactions/heatmap", # Corrected path
    response_model=Dict[str, Any], # Replace with specific schema later if desired
    tags=["Dashboard"],
    summary="Get Aggregated Heatmap Data for a Target Element"
)
async def get_dashboard_heatmap_data(
    target: str = Query(..., description="Identifier of the HTML element for heatmap aggregation (e.g., 'pdf-viewer')"),
    service: DashboardService = Depends(get_dashboard_service),
    current_researcher: Researcher = AuthDependency # Apply auth dependency
):
    """
    Retrieves aggregated interaction data (e.g., clicks, processed mouse moves)
    suitable for generating a heatmap overlay for a specific UI element.
    Data is anonymized and aggregated (e.g., {x, y, value} points).
    (Requires researcher authentication).
    """
    try:
        heatmap_data = await service.get_aggregated_heatmap_data(target_element_id=target)
        return heatmap_data
    except Exception as e:
        # Log the exception e
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to retrieve heatmap data: {e}"
        )

@router.get(
    "/interactions/pdf", # Corrected path
    response_model=Dict[str, Any], # Replace with specific schema later if desired
    tags=["Dashboard"],
    summary="Get Aggregated Interaction Statistics for a Specific PDF"
)
async def get_dashboard_pdf_interaction_data(
    pdf_url: str = Query(..., description="URL or identifier of the PDF document"),
    service: DashboardService = Depends(get_dashboard_service),
    current_researcher: Researcher = AuthDependency # Apply auth dependency
):
    """
    Retrieves aggregated interaction statistics for a specific PDF document,
    such as page view durations, scroll depth analysis, zoom usage, text selections.
    Results are anonymized.
    (Requires researcher authentication).
    Note: Full aggregation logic might be complex and is simplified in the service.
    """
    try:
        pdf_data = await service.get_aggregated_pdf_interaction_data(pdf_url=pdf_url)
        return pdf_data
    except Exception as e:
        # Log the exception e
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to retrieve PDF interaction data: {e}"
        )