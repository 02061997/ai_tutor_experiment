# backend/api/deps.py
# Removed import of unused AdaptiveQuizService

from typing import Generator, Optional, Dict, Any, AsyncGenerator, List # Added List
from fastapi import Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer
from jose import JWTError, jwt # Added jwt
from pydantic import ValidationError, EmailStr, BaseModel # Added BaseModel
from sqlmodel.ext.asyncio.session import AsyncSession

from backend.core.config import settings
from backend.db.database import AsyncSessionFactory # Use correct name
from backend.core import security
from backend.schemas.token import TokenData
from backend.db.models import Researcher

# --- Import Services --- Needed for dependency functions below
from backend.services.auth_service import AuthService

# Import other needed services...
from backend.services.consent_service import ConsentService
from backend.services.interaction_service import InteractionService
from backend.services.survey_service import SurveyService
from backend.services.test_service import TestService
from backend.services.app1_service import App1Service
from backend.services.app2_service import App2Service
from backend.services.dashboard_service import DashboardService
# --- NEW SERVICE IMPORT ---
from backend.services.llm_quiz_service import LLMQuizService # <-- Keep this one
# --- End Service Imports ---


# --- Database Session Dependency ---
async def get_session() -> AsyncGenerator[AsyncSession, None]:
    """
    Async dependency that provides a database session per request.
    """
    async with AsyncSessionFactory() as session:
        try:
            yield session
        except Exception:
            await session.rollback()
            raise
        # Commit/Close handled by context manager or wrapper


# --- Authentication Dependencies ---
oauth2_scheme = OAuth2PasswordBearer(
    tokenUrl=f"{settings.API_V1_STR}/auth/token"
)

def get_auth_service(session: AsyncSession = Depends(get_session)) -> AuthService:
    return AuthService(session=session)

async def get_current_researcher(
    token: str = Depends(oauth2_scheme),
    service: AuthService = Depends(get_auth_service)
) -> Researcher:
    # (Keep implementation as provided previously)
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Could not validate credentials",
        headers={"WWW-Authenticate": "Bearer"},
    )
    forbidden_exception = HTTPException(
        status_code=status.HTTP_403_FORBIDDEN,
        detail="User does not have sufficient privileges."
    )
    try:
        payload = jwt.decode(token, settings.SECRET_KEY, algorithms=[settings.ALGORITHM])
        email: Optional[str] = payload.get("sub")
        roles: Optional[List[str]] = payload.get("roles", [])
        if email is None: raise credentials_exception
        # token_data = TokenData(sub=email, roles=roles) # Optional validation step
    except JWTError as e: raise credentials_exception from e
    researcher = await service.get_researcher_by_email(email=email)
    if researcher is None: raise credentials_exception
    if not researcher.is_active: raise credentials_exception
    if "researcher" not in roles: raise forbidden_exception
    return researcher


# --- Function for LLM Quiz Service Dependency ---
def get_llm_quiz_service(session: AsyncSession = Depends(get_session)) -> LLMQuizService:
    """Dependency function to get an instance of the LLMQuizService."""
    return LLMQuizService(session=session)
# --- End LLM Quiz Service Dependency ---

# --- Optional: Add Dependency Functions for Other Services ---
def get_consent_service(session: AsyncSession = Depends(get_session)) -> ConsentService:
    return ConsentService(session=session)

def get_interaction_service(session: AsyncSession = Depends(get_session)) -> InteractionService:
    return InteractionService(session=session)

def get_survey_service(session: AsyncSession = Depends(get_session)) -> SurveyService:
    return SurveyService(session=session)

def get_test_service(session: AsyncSession = Depends(get_session)) -> TestService:
    return TestService(session=session)

def get_app1_service(session: AsyncSession = Depends(get_session)) -> App1Service:
    return App1Service(session=session, groq_api_key=getattr(settings, 'GROQ_API_KEY', None))

def get_app2_service(session: AsyncSession = Depends(get_session)) -> App2Service:
    return App2Service(session=session, google_api_key=settings.GOOGLE_API_KEY)

def get_dashboard_service(session: AsyncSession = Depends(get_session)) -> DashboardService:
    return DashboardService(session=session)
# --- End Other Service Dependencies ---