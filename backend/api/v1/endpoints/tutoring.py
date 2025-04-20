# backend/api/v1/endpoints/tutoring.py

import os
from fastapi import APIRouter, HTTPException, status
from fastapi.responses import FileResponse

router = APIRouter()

# Define the path to the frontend directory relative to the project root
# Adjust this if your execution context is different
FRONTEND_DIR = "frontend"
APP2_HTML_FILE = "app2_tutor.html"
APP2_HTML_PATH = os.path.join(FRONTEND_DIR, APP2_HTML_FILE)

@router.get(
    "/app",
    response_class=FileResponse, # Specify the response type
    tags=["Tutoring App"],
    summary="Serve the Main Tutoring Application (App2)"
)
async def serve_tutoring_app():
    """
    Serves the main HTML file for the App2 tutoring interface.
    """
    if not os.path.exists(APP2_HTML_PATH):
        print(f"Error: Cannot find App2 HTML file at expected path: {os.path.abspath(APP2_HTML_PATH)}")
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Application file '{APP2_HTML_FILE}' not found. Searched at: {APP2_HTML_PATH}"
        )
    return FileResponse(APP2_HTML_PATH)

# Add any other App2-specific API endpoints here if they arise later
# For example, endpoints related to LLM calls specifically for App2 features
# (like summaries/recommendations if not handled elsewhere).