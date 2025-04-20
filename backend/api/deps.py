# backend/api/deps.py

from typing import Generator, Optional, Dict, Any

from fastapi import Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer
from jose import JWTError
from pydantic import ValidationError, EmailStr
from sqlmodel.ext.asyncio.session import AsyncSession

from backend.core.config import settings
from backend.db.database import get_session # Reuse get_session from database.py
from backend.core import security # Import security utilities
from backend.schemas.token import TokenData # Import schema for token payload
from backend.db.models import Researcher # Import Researcher model
from backend.services.auth_service import AuthService # Import AuthService

# Define the OAuth2 scheme
oauth2_scheme = OAuth2PasswordBearer(
    tokenUrl=f"{settings.API_V1_STR}/auth/token"
)

# Dependency function to get the auth service instance (needed for user lookup)
def get_auth_service(session: AsyncSession = Depends(get_session)) -> AuthService:
    return AuthService(session=session)


async def get_current_researcher(
    token: str = Depends(oauth2_scheme),
    service: AuthService = Depends(get_auth_service) # Inject AuthService
) -> Researcher: # Return the actual Researcher DB model object
    """
    Dependency to:
    1. Verify the access token (signature, expiry).
    2. Retrieve researcher details from the database based on token data.
    3. Check if the researcher is active and has the required role.

    Returns:
        The authenticated Researcher database object.

    Raises:
        HTTPException 401: If token is invalid, expired, or user not found/inactive.
        HTTPException 403: If user lacks the required 'researcher' role.
    """
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
        # Step 1: Verify the token structure and claims
        token_data = security.verify_access_token(
            token=token, credentials_exception=credentials_exception
        )

        # Step 2: Retrieve the researcher from DB using email from token's subject
        # Ensure 'sub' contains the email address used for lookup
        if not token_data.sub or not EmailStr.validate(token_data.sub):
             print("Token verification error: Token subject is missing or not a valid email.")
             raise credentials_exception

        researcher = await service.get_researcher_by_email(email=token_data.sub)

        if researcher is None:
            print(f"Authentication error: Researcher '{token_data.sub}' from token not found in DB.")
            raise credentials_exception

        # Step 3: Check if researcher is active
        if not researcher.is_active:
            print(f"Authentication error: Researcher '{token_data.sub}' is inactive.")
            raise credentials_exception # Or maybe 403 Forbidden? 401 seems appropriate.

        # Step 4: Check for required role (using roles embedded in token for simplicity)
        # Alternatively, roles could be stored on the Researcher model in DB
        if not token_data.roles or "researcher" not in token_data.roles:
             print(f"Authorization error: Researcher '{token_data.sub}' lacks 'researcher' role in token.")
             raise forbidden_exception # Use 403 Forbidden for role issues

        # Step 5: Return the database model object for the authenticated researcher
        return researcher

    except (JWTError, ValidationError) as e:
        # Catch errors from verify_access_token
        print(f"Auth error in get_current_researcher (Token Validation): {e}")
        raise credentials_exception
    except HTTPException as e:
        # Re-raise HTTPExceptions raised downstream (e.g., 403 from role check)
        raise e
    except Exception as e:
        # Catch unexpected errors during DB lookup etc.
        print(f"Auth error in get_current_researcher (Unexpected): {e}")
        # Don't expose internal error details, raise standard credentials exception
        raise credentials_exception