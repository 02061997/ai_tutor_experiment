# backend/api/v1/endpoints/auth.py
# Corrected Version (Path prefix removed)

from datetime import timedelta

from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.security import OAuth2PasswordRequestForm # Standard form dependency
from sqlmodel.ext.asyncio.session import AsyncSession

# Dependency for DB session
from backend.db.database import get_session

# Service, Security utils, and Schemas
from backend.services.auth_service import AuthService
from backend.core.security import create_access_token, ACCESS_TOKEN_EXPIRE_MINUTES
from backend.schemas.token import Token


# Dependency function to get the auth service instance
def get_auth_service(session: AsyncSession = Depends(get_session)) -> AuthService:
    return AuthService(session=session)


router = APIRouter()

@router.post(
    "/token", # Corrected path (removed /auth prefix)
    response_model=Token,
    tags=["Authentication"]
)
async def login_for_access_token(
    form_data: OAuth2PasswordRequestForm = Depends(), # Uses form data: username & password
    service: AuthService = Depends(get_auth_service)
):
    """
    OAuth2 compatible token login endpoint.
    Provides an access token for authenticated researchers.

    Takes username (which is the researcher's email) and password
    as form data.
    """
    # Use the AuthService to authenticate the researcher
    # Note: OAuth2PasswordRequestForm uses 'username' field for the identifier
    researcher = await service.authenticate_researcher(
        email=form_data.username, # Map form's username field to email
        password=form_data.password
    )

    if not researcher:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect email or password",
            headers={"WWW-Authenticate": "Bearer"}, # Required header for 401
        )

    # Create the data payload for the JWT token
    access_token_expires = timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
    # Include relevant, non-sensitive info in the token payload
    token_data = {
        "sub": researcher.email, # 'sub' (subject) is standard, using email here
        "user_id": str(researcher.researcher_id), # Include user ID as string
        "roles": ["researcher"] # Add role information (customize if needed)
        # Add other claims like 'exp' (handled by create_access_token), 'iat', 'iss', 'aud' if needed
    }
    access_token = create_access_token(
        data=token_data, expires_delta=access_token_expires
    )

    # Return the token
    return Token(access_token=access_token, token_type="bearer")