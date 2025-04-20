# backend/api/v1/endpoints/base.py

from fastapi import APIRouter

router = APIRouter()

@router.get("/", tags=["Base"])
async def read_root():
    """
    Root endpoint for health check.
    """
    return {"message": "AI Tutor Experiment API is running!"}

# Add any other base/utility endpoints here if needed