# backend/core/security.py

from datetime import datetime, timedelta, timezone
from typing import Optional, Any, Union
import uuid # Import uuid

# Make sure jose is installed: pip install python-jose[cryptography]
from jose import JWTError, jwt, ExpiredSignatureError
from passlib.context import CryptContext

from backend.core.config import settings
from backend.schemas.token import TokenData # Import the schema for token payload

# Password Hashing Context
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

# JWT Configuration
SECRET_KEY = settings.SECRET_KEY
ALGORITHM = settings.ALGORITHM
ACCESS_TOKEN_EXPIRE_MINUTES = settings.ACCESS_TOKEN_EXPIRE_MINUTES


def verify_password(plain_password: str, hashed_password: str) -> bool:
    """Verifies a plain password against a hashed password."""
    return pwd_context.verify(plain_password, hashed_password)

def get_password_hash(password: str) -> str:
    """Hashes a plain password using bcrypt."""
    return pwd_context.hash(password)

def create_access_token(
    data: dict, expires_delta: Optional[timedelta] = None
) -> str:
    """
    Creates a JWT access token.
    """
    to_encode = data.copy()
    if expires_delta:
        expire = datetime.now(timezone.utc) + expires_delta
    else:
        expire = datetime.now(timezone.utc) + timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
    to_encode.update({"exp": expire, "iat": datetime.now(timezone.utc)}) # Add issued-at time
    # Ensure 'sub' (subject) is present
    if 'sub' not in to_encode:
        if 'username' in to_encode:
             to_encode['sub'] = to_encode['username']
        elif 'user_id' in to_encode:
              to_encode['sub'] = str(to_encode['user_id'])

    encoded_jwt = jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)
    return encoded_jwt

def verify_access_token(token: str, credentials_exception: Exception) -> TokenData:
    """
    Verifies the access token: checks signature, expiry, and extracts claims.

    Args:
        token: The JWT token string.
        credentials_exception: Exception to raise if validation fails.

    Returns:
        TokenData object with payload data if valid.

    Raises:
        credentials_exception: If token is invalid (expired, bad signature, missing claims).
    """
    try:
        payload = jwt.decode(
            token,
            SECRET_KEY,
            algorithms=[ALGORITHM],
            # Add options like audience validation if needed:
            # options={"verify_aud": True},
            # audience="YOUR_AUDIENCE"
        )
        # Extract standard claims
        username: Optional[str] = payload.get("sub") # 'sub' is standard claim for subject
        user_id_str: Optional[str] = payload.get("user_id")
        roles: Optional[list[str]] = payload.get("roles")

        if username is None and user_id_str is None:
            print("Token verification error: Token missing subject ('sub' or 'user_id').")
            raise credentials_exception # Raise exception if no identifier found

        # Attempt to convert user_id to UUID if present
        user_id = None
        if user_id_str:
            try:
                user_id = uuid.UUID(user_id_str)
            except ValueError:
                print(f"Token verification error: Invalid UUID format for user_id: {user_id_str}")
                raise credentials_exception

        # Create TokenData object
        token_data = TokenData(username=username, user_id=user_id, roles=roles)
        print(f"DEBUG: Token verified for: {token_data}") # Debug print
        return token_data

    except ExpiredSignatureError:
        print("Token verification error: Token has expired.")
        raise credentials_exception
    except JWTError as e:
        # Catch other JOSE errors (e.g., invalid signature, invalid format)
        print(f"Token verification error: Invalid token: {e}")
        raise credentials_exception
    except Exception as e:
        # Catch potential UUID conversion error or others during parsing
        print(f"Token verification error: Unexpected issue: {e}")
        raise credentials_exception