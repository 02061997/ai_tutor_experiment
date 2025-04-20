# backend/services/dashboard_service.py

import uuid
from datetime import datetime
from typing import List, Optional, Dict, Any
from collections import Counter
import json # For safely parsing JSON payloads if needed
import numpy as np

# SQLAlchemy core functions for aggregation
from sqlalchemy import func, cast, JSON, select, text, case
from sqlalchemy.orm import Session # For potential sync operations if needed, though stick to async
from sqlmodel.ext.asyncio.session import AsyncSession

# Project components
from backend.db.models import (
    Consent,
    SurveyResponse,
    QuizAttemptState,
    InteractionLog,
    QuizQuestion
)
# Schemas for dashboard data structures will be defined in schemas/dashboard.py
# For now, we return dictionaries matching the structure in Table 8 of the plan

# Optional: Import pandas for more advanced aggregation if available
try:
    import pandas as pd
    PANDAS_AVAILABLE = True
except ImportError:
    PANDAS_AVAILABLE = False
    print("Warning: Pandas not installed. Dashboard aggregations will be limited.")

class DashboardService:
    """
    Service layer for querying and aggregating data for the researcher dashboard.
    IMPORTANT: Methods should only return aggregated and anonymized data.
    """

    def __init__(self, session: AsyncSession):
        self.session = session

    async def get_experiment_summary(self) -> Dict[str, Any]:
        """
        Provides overall experiment statistics like participant counts and completion rates.
        Corresponds to endpoint: GET /dashboard/api/summary
        """
        stmt = (
            select(
                func.count(Consent.session_uuid).label("total_participants"),
                func.sum(case((Consent.session_status == 'Completed', 1), else_=0)).label("completed_count"),
                func.sum(case((Consent.assigned_app == 'App1', 1), else_=0)).label("app1_count"),
                func.sum(case((Consent.assigned_app == 'App2', 1), else_=0)).label("app2_count"),
                # Add more aggregations as needed (e.g., completion by app type)
            )
        )
        # Note: `case` might need to be imported from sqlalchemy or constructed differently
        # depending on exact sqlalchemy version. Using basic func.sum for illustration.
        # Alternative using group_by (might require separate queries):
        total_participants_res = await self.session.execute(select(func.count(Consent.session_uuid)))
        total_participants = total_participants_res.scalar_one_or_none() or 0

        status_counts_res = await self.session.execute(
            select(Consent.session_status, func.count(Consent.session_uuid))
            .group_by(Consent.session_status)
        )
        status_counts = {status: count for status, count in status_counts_res.all()}

        app_counts_res = await self.session.execute(
             select(Consent.assigned_app, func.count(Consent.session_uuid))
             .group_by(Consent.assigned_app)
        )
        app_counts = {app: count for app, count in app_counts_res.all()}


        return {
            "total_participants": total_participants,
            "completed_participants": status_counts.get('Completed', 0),
            "abandoned_participants": status_counts.get('Abandoned', 0),
            "error_participants": status_counts.get('Error', 0),
            "assigned_app1_count": app_counts.get('App1', 0),
            "assigned_app2_count": app_counts.get('App2', 0),
            # Calculate completion rates if needed
            "completion_rate": (status_counts.get('Completed', 0) / total_participants * 100) if total_participants > 0 else 0,
        }

    async def get_aggregated_survey_results(self, survey_type: str, question_key: str) -> Dict[str, Any]:
        """
        Provides aggregated results for a specific question within a specific survey type.
        Corresponds to endpoint: GET /dashboard/api/survey/results?survey_type=...&question_key=...

        Args:
            survey_type: The type of survey (e.g., 'experience_app1', 'exit').
            question_key: The key identifying the question within the 'responses' JSON dict.

        Returns:
            Aggregated data (e.g., counts per option).
        """
        stmt = select(SurveyResponse.responses).where(SurveyResponse.survey_type == survey_type)
        results = await self.session.execute(stmt)
        all_responses_json = results.scalars().all()

        # Aggregate in Python (can be slow for large datasets)
        answer_counts = Counter()
        total_responses_for_question = 0
        for resp_json in all_responses_json:
            if isinstance(resp_json, dict) and question_key in resp_json:
                answer = resp_json[question_key]
                # Handle potential variations in answer format (string, number, list)
                if isinstance(answer, list): # Handle multi-select if applicable
                    for item in answer:
                        answer_counts[str(item)] += 1
                else:
                    answer_counts[str(answer)] += 1
                total_responses_for_question += 1

        return {
            "survey_type": survey_type,
            "question_key": question_key,
            "total_responses_for_question": total_responses_for_question,
            "response_counts": dict(answer_counts)
        }
        # Note: If using Pandas, this could be much more efficient:
        # df = pd.read_sql(stmt, self.session.bind)
        # df['answer'] = df['responses'].apply(lambda x: x.get(question_key) if isinstance(x, dict) else None)
        # aggregated = df['answer'].value_counts().to_dict() ...

    async def get_aggregated_quiz_performance(self) -> Dict[str, Any]:
        """
        Provides aggregated performance metrics from completed quiz attempts.
        Corresponds to endpoint: GET /dashboard/api/quiz/performance
        """
        # Select relevant metrics from completed attempts
        stmt = select(
                QuizAttemptState.current_theta,
                QuizAttemptState.current_se,
                func.json_array_length(QuizAttemptState.administered_items).label("items_administered") # Requires JSON support in DB
                # Cast administered_items to TEXT then use length if json_array_length not available
                # func.length(cast(QuizAttemptState.administered_items, Text)).label("items_len_approx") # Less accurate
            ).where(QuizAttemptState.is_complete == True)

        results = await self.session.execute(stmt)
        performance_data = results.fetchall() # Fetchall might be memory intensive for many attempts

        if not performance_data:
             return {"message": "No completed quiz attempts found."}

        # Aggregate using Python (or ideally Pandas if available)
        thetas = [row.current_theta for row in performance_data if row.current_theta is not None]
        ses = [row.current_se for row in performance_data if row.current_se is not None]
        item_counts = [row.items_administered for row in performance_data if row.items_administered is not None] # Assumes items_administered is the length

        avg_theta = np.mean(thetas) if thetas else None
        avg_se = np.mean(ses) if ses else None
        avg_items = np.mean(item_counts) if item_counts else None
        median_theta = np.median(thetas) if thetas else None

        # For distribution, calculate histogram bins/counts
        theta_hist = {}
        if thetas:
             hist, bin_edges = np.histogram(thetas, bins=10) # Example: 10 bins
             theta_hist = {"counts": hist.tolist(), "bin_edges": bin_edges.tolist()}


        return {
            "total_completed_attempts": len(performance_data),
            "average_final_theta": avg_theta,
            "median_final_theta": median_theta,
            "average_final_se": avg_se,
            "average_items_administered": avg_items,
            "theta_distribution": theta_hist,
            # Add more stats: SD, min, max, percentiles etc.
        }

    async def get_aggregated_heatmap_data(self, target_element_id: str) -> Dict[str, Any]:
        """
        Provides aggregated data for heatmap generation.
        Corresponds to endpoint: GET /dashboard/api/interactions/heatmap?target=...

        Args:
            target_element_id: The identifier of the element to aggregate data for.

        Returns:
            Aggregated data suitable for heatmap.js (e.g., list of {x, y, value}).
        """
        # Fetching potentially large amounts of coordinates
        # This query could be very slow and memory-intensive without optimization
        stmt = select(InteractionLog.payload).where(
            InteractionLog.target_element_id == target_element_id,
            # Add filter for event_type if needed (e.g., 'click', 'mousemove_batch')
            InteractionLog.event_type.in_(['click', 'mousemove_batch']) # Example filter
        )
        results = await self.session.execute(stmt)
        payloads = results.scalars().all()

        # Aggregate in Python (Inefficient for large data)
        # Assumes payload contains 'x', 'y' for clicks, or a list of points for 'mousemove_batch'
        points_value = Counter()
        for p in payloads:
            if isinstance(p, dict):
                if 'value' in p and 'x' in p and 'y' in p: # Simple click format {x, y, value=1}
                    coord = (p.get('x'), p.get('y'))
                    if coord[0] is not None and coord[1] is not None:
                         points_value[coord] += p.get('value', 1) # Increment value
                elif 'points' in p and isinstance(p['points'], list): # Batch format { points: [{x, y, value}, ...]}
                     for point in p['points']:
                         if isinstance(point, dict) and 'x' in point and 'y' in point:
                            coord = (point.get('x'), point.get('y'))
                            if coord[0] is not None and coord[1] is not None:
                                points_value[coord] += point.get('value', 1)

        # Convert Counter to list format required by heatmap.js [{x, y, value}, ...]
        heatmap_data = [{"x": k[0], "y": k[1], "value": v} for k, v in points_value.items()]

        # TODO: Implement grid-based aggregation for better performance/scaling
        # e.g., define grid size, calculate which cell each point falls into, count points per cell

        return {
            "target": target_element_id,
            "heatmap_data": heatmap_data, # List of {x, y, value}
            "aggregation_method": "simple_coordinate_count" # Indicate method used
        }

    # --- Placeholder for more complex aggregations ---

    async def get_aggregated_pdf_interaction_data(self, pdf_url: str) -> Dict[str, Any]:
        """
        Provides aggregated interaction statistics for a specific PDF.
        Corresponds to endpoint: GET /dashboard/api/interactions/pdf?pdf_url=...
        **Note:** This requires significant processing logic. Placeholder implementation.
        """
        # Fetch all interaction logs for this PDF
        stmt = select(InteractionLog.event_type, InteractionLog.payload, InteractionLog.timestamp)\
            .where(InteractionLog.pdf_url == pdf_url)\
            .order_by(InteractionLog.timestamp) # Order matters for duration calculations

        results = await self.session.execute(stmt)
        logs = results.all()

        if not logs:
             return {"message": f"No interaction data found for PDF: {pdf_url}"}

        # **Complex Processing Required Here**
        # - Calculate page view durations from consecutive 'pdf_page_view' events.
        # - Aggregate maximum scroll depth per page/session from 'pdf_scroll' events.
        # - Count zoom levels/changes from 'pdf_zoom' events.
        # - Count occurrences of selected text from 'pdf_text_select' events.
        # This is best done using Pandas after fetching the data.

        # Example (Simplified): Count event types
        event_counts = Counter(log.event_type for log in logs)

        # Example (Simplified): Count top text selections
        text_selections = Counter()
        for log in logs:
             if log.event_type == 'pdf_text_select' and isinstance(log.payload, dict):
                 selected_text = log.payload.get('selected_text')
                 if selected_text:
                     text_selections[selected_text] += 1


        return {
            "pdf_url": pdf_url,
            "total_interactions_logged": len(logs),
            "event_type_counts": dict(event_counts),
            "top_text_selections": dict(text_selections.most_common(10)), # Top 10
            "message": "Note: PDF aggregation is simplified. Full analysis requires more processing (e.g., using Pandas)."
            # Add keys for: avg_time_per_page, scroll_depth_histogram, zoom_actions_count etc.
            # based on the complex processing mentioned above.
        }

    async def get_aggregated_item_analysis(self, question_id: uuid.UUID) -> Dict[str, Any]:
        """
        Provides aggregated statistics for a specific quiz item.
        Corresponds to endpoint: GET /dashboard/api/quiz/item_analysis/{question_id}
        **Note:** Requires parsing JSON lists, potentially slow. Placeholder implementation.
        """
        question_id_str = str(question_id)

        # Fetch attempts where this question was administered
        # This query is complex as it needs to check inside a JSON array
        # Using raw SQL or specific JSON functions might be necessary and DB-dependent
        # Placeholder using a less efficient approach: fetch relevant fields and process in Python
        stmt = select(QuizAttemptState.administered_items, QuizAttemptState.responses)\
            .where(QuizAttemptState.is_complete == True) # Analyze completed attempts

        results = await self.session.execute(stmt)
        attempts = results.all()

        total_administrations = 0
        correct_responses = 0

        for attempt in attempts:
            try:
                # Find the index of the question in this attempt's administered list
                item_index = attempt.administered_items.index(question_id_str)
                total_administrations += 1
                # Check the corresponding response (0 or 1)
                if len(attempt.responses) > item_index and attempt.responses[item_index] == 1:
                    correct_responses += 1
            except (ValueError, IndexError):
                # Question not found in this attempt's list or response list mismatch
                continue

        p_value = (correct_responses / total_administrations) if total_administrations > 0 else None

        # TODO: Add point-biserial calculation (requires theta values for each participant who took the item)

        return {
            "question_id": question_id_str,
            "total_administrations": total_administrations,
            "correct_response_count": correct_responses,
            "p_value (difficulty)": p_value, # Proportion correct
            "message": "Note: Item analysis is simplified. Point-biserial calculation requires additional data/logic."
        }