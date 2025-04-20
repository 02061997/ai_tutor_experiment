# backend/api/v1/router.py

from fastapi import APIRouter
from backend.api.v1.endpoints import auth

# Import individual endpoint routers
from backend.api.v1.endpoints import base
from backend.api.v1.endpoints import consent
from backend.api.v1.endpoints import survey
from backend.api.v1.endpoints import interaction
from backend.api.v1.endpoints import quiz
from backend.api.v1.endpoints import dashboard
from backend.api.v1.endpoints import test
from backend.api.v1.endpoints import app1
# Import tutoring endpoint router if/when created
# from backend.api.v1.endpoints import tutoring

# Main router for API version 1
api_router_v1 = APIRouter()

# Include endpoint routers into the main v1 router
api_router_v1.include_router(base.router, prefix="", tags=["Base"])
api_router_v1.include_router(consent.router, prefix="/consent", tags=["Consent & Session"]) # Prefix added here
api_router_v1.include_router(survey.router, prefix="/survey", tags=["Survey"]) # Prefix added here
api_router_v1.include_router(interaction.router, prefix="/interaction", tags=["Interaction"]) # Prefix added here
api_router_v1.include_router(quiz.router, prefix="/quiz", tags=["Quiz"]) # Prefix added here
api_router_v1.include_router(dashboard.router, prefix="/dashboard", tags=["Dashboard"]) # Prefix added here
api_router_v1.include_router(auth.router, prefix="/auth", tags=["Authentication"])
api_router_v1.include_router(test.router, prefix="/final-test", tags=["Test"])
api_router_v1.include_router(app1.router, prefix="/app1", tags=["App1"])
# api_router_v1.include_router(tutoring.router, prefix="/tutoring", tags=["Tutoring"]) # Example if tutoring endpoints exist