# backend/services/dashboard_service.py
# Refactored for RAG/LLM Quiz data (MCQAttempt) - Ensure this replaces old version

import uuid
from datetime import datetime
from typing import List, Optional, Dict, Any
from collections import Counter
import json
import numpy as np
import logging # Added logger

# SQLAlchemy core functions for aggregation
from sqlalchemy import func, cast, JSON, select, text, case
# from sqlalchemy.orm import Session # Not used directly in async methods
from sqlmodel.ext.asyncio.session import AsyncSession

# Project components
from backend.db.models import (
    Consent,
    SurveyResponse,
    # QuizAttemptState, # Removed old model import
    InteractionLog,
    # QuizQuestion, # Removed old model import
    MCQAttempt # <-- Import NEW model
)

# Optional: Import pandas for more advanced aggregation if available
try:
    import pandas as pd
    PANDAS_AVAILABLE = True
except ImportError:
    PANDAS_AVAILABLE = False
    # Use logger instead of print
    logging.warning("Pandas not installed. Dashboard aggregations will use basic SQL/Python.")

logger = logging.getLogger(__name__)

class DashboardService:
    """
    Service layer for querying and aggregating data for the researcher dashboard.
    Updated to use MCQAttempt for quiz performance metrics.
    """

    def __init__(self, session: AsyncSession):
        self.session = session

    async def get_experiment_summary(self) -> Dict[str, Any]:
        """
        Provides overall experiment statistics like participant counts and completion rates.
        """
        logger.info("Fetching experiment summary statistics...")
        # Using separate queries for clarity and potential DB compatibility
        total_participants_res = await self.session.execute(select(func.count(Consent.session_uuid)))
        total_participants = total_participants_res.scalar_one_or_none() or 0

        status_counts_res = await self.session.execute(
            select(Consent.session_status, func.count(Consent.session_uuid))
            .group_by(Consent.session_status)
        )
        status_counts = {status or "Unknown": count for status, count in status_counts_res.all()}

        app_counts_res = await self.session.execute(
            select(Consent.assigned_app, func.count(Consent.session_uuid))
            .group_by(Consent.assigned_app)
        )
        app_counts = {app or "Unknown": count for app, count in app_counts_res.all()}

        completion_rate = (status_counts.get('Completed', 0) / total_participants * 100) if total_participants > 0 else 0

        summary = {
            "total_participants": total_participants,
            "status_counts": status_counts, # Provides counts for Completed, Abandoned, Error, Unknown
            "app_assignment_counts": app_counts,
            "completion_rate_percent": round(completion_rate, 2),
        }
        logger.debug(f"Experiment summary generated: {summary}")
        return summary

    async def get_aggregated_survey_results(self, survey_type: str, question_key: str) -> Dict[str, Any]:
        """
        Provides aggregated results for a specific question within a specific survey type.
        """
        logger.info(f"Fetching aggregated survey results for type='{survey_type}', question='{question_key}'")
        stmt = select(SurveyResponse.responses).where(SurveyResponse.survey_type == survey_type)
        results = await self.session.execute(stmt)
        all_responses_json = results.scalars().all()

        answer_counts = Counter()
        total_responses_for_question = 0
        for resp_json in all_responses_json:
            if isinstance(resp_json, dict) and question_key in resp_json:
                answer = resp_json[question_key]
                if isinstance(answer, list):
                    for item in answer:
                        answer_counts[str(item)] += 1
                else:
                    answer_counts[str(answer)] += 1
                total_responses_for_question += 1
            elif resp_json is not None:
                logger.warning(f"Survey response payload is not a dict or missing key '{question_key}': {resp_json}")


        results = {
            "survey_type": survey_type,
            "question_key": question_key,
            "total_responses_for_question": total_responses_for_question,
            "response_counts": dict(answer_counts)
        }
        logger.debug(f"Aggregated survey results: {results}")
        return results

    async def get_aggregated_quiz_performance(self) -> Dict[str, Any]:
        """
        Provides aggregated performance metrics from the new LLM quiz attempts (MCQAttempt).
        """
        logger.info("Fetching aggregated LLM quiz performance...")
        # Query MCQAttempt table
        stmt = select(
            func.count(MCQAttempt.attempt_id).label("total_attempts"),
            func.sum(case((MCQAttempt.is_correct == True, 1), else_=0)).label("correct_attempts"),
            func.count(func.distinct(MCQAttempt.session_uuid)).label("unique_participants"),
            func.count(func.distinct(MCQAttempt.mcq_id)).label("unique_questions_attempted")
        )

        result = await self.session.execute(stmt)
        row = result.first()

        if not row or row.total_attempts == 0:
            logger.info("No MCQ attempts found for aggregation.")
            return {"message": "No quiz attempts found for the LLM quiz."}

        total_attempts = row.total_attempts or 0
        correct_attempts = row.correct_attempts or 0
        unique_participants = row.unique_participants or 0
        unique_questions_attempted = row.unique_questions_attempted or 0

        overall_accuracy = (correct_attempts / total_attempts * 100) if total_attempts > 0 else 0
        avg_attempts_per_participant = (total_attempts / unique_participants) if unique_participants > 0 else 0

        performance_data = {
            "quiz_type": "LLM_Generated",
            "total_attempts_recorded": total_attempts,
            "total_correct_attempts": correct_attempts,
            "overall_accuracy_percent": round(overall_accuracy, 2),
            "unique_participants_with_attempts": unique_participants,
            "unique_questions_attempted": unique_questions_attempted,
            "average_attempts_per_participant": round(avg_attempts_per_participant, 2),
        }
        logger.debug(f"Aggregated LLM quiz performance: {performance_data}")
        return performance_data

    async def get_aggregated_heatmap_data(self, target_element_id: str) -> Dict[str, Any]:
        """
        Provides aggregated data for heatmap generation.
        """
        logger.info(f"Fetching aggregated heatmap data for target='{target_element_id}'")
        stmt = select(InteractionLog.payload).where(
            InteractionLog.target_element_id == target_element_id,
            InteractionLog.event_type.in_(['click', 'mousemove_batch'])
        )
        results = await self.session.execute(stmt)
        payloads = results.scalars().all()

        points_value = Counter()
        processed_logs = 0
        for p in payloads:
            processed_logs += 1
            if isinstance(p, dict):
                if 'value' in p and 'x' in p and 'y' in p:
                    try:
                        coord = (int(p.get('x')), int(p.get('y')))
                        points_value[coord] += int(p.get('value', 1))
                    except (TypeError, ValueError): continue
                elif 'points' in p and isinstance(p['points'], list):
                    for point in p['points']:
                        if isinstance(point, dict) and 'x' in point and 'y' in point:
                            try:
                                coord = (int(point.get('x')), int(point.get('y')))
                                points_value[coord] += int(point.get('value', 1))
                            except (TypeError, ValueError): continue

        heatmap_data = [{"x": k[0], "y": k[1], "value": v} for k, v in points_value.items()]
        logger.debug(f"Generated heatmap data with {len(heatmap_data)} points from {processed_logs} logs for target '{target_element_id}'.")

        return {
            "target": target_element_id,
            "heatmap_data": heatmap_data,
            "aggregation_method": "simple_coordinate_count"
        }

    async def get_aggregated_pdf_interaction_data(self, pdf_url: str) -> Dict[str, Any]:
        """
        Provides aggregated interaction statistics for a specific PDF.
        """
        logger.info(f"Fetching aggregated PDF interaction data for url='{pdf_url}'")
        stmt = select(InteractionLog.event_type, InteractionLog.payload, InteractionLog.timestamp) \
            .where(InteractionLog.pdf_url == pdf_url) \
            .order_by(InteractionLog.timestamp)

        results = await self.session.execute(stmt)
        logs = results.all()

        if not logs:
            logger.info(f"No interaction data found for PDF: {pdf_url}")
            return {"message": f"No interaction data found for PDF: {pdf_url}"}

        event_counts = Counter(log.event_type for log in logs)
        text_selections = Counter()
        for log in logs:
            if log.event_type == 'pdf_text_select' and isinstance(log.payload, dict):
                selected_text = log.payload.get('selected_text')
                if selected_text and isinstance(selected_text, str):
                    text_selections[selected_text.strip()] += 1

        pdf_data = {
            "pdf_url": pdf_url,
            "total_interactions_logged": len(logs),
            "event_type_counts": dict(event_counts),
            "top_text_selections": dict(text_selections.most_common(10)),
            "message": "Note: PDF aggregation is simplified. Full analysis requires more processing."
        }
        logger.debug(f"Aggregated PDF interaction data generated for {pdf_url}.")
        return pdf_data
