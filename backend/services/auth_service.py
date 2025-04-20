# backend/services/auth_service.py
# Corrected version with 'await' added before session.exec call

from typing import Optional

from sqlmodel import select
from sqlmodel.ext.asyncio.session import AsyncSession

# Import the Researcher model and schema
from backend.db.models import Researcher
from backend.schemas.researcher import ResearcherCreate

# Import password hashing utilities
from backend.core.security import verify_password, get_password_hash


class AuthService:
    """
    Service layer for handling researcher authentication and potentially creation.
    """

    def __init__(self, session: AsyncSession):
        """
        Initializes the service with an async database session.

        Args:
            session: The database session dependency.
        """
        self.session = session

    async def get_researcher_by_email(self, email: str) -> Optional[Researcher]:
        """
        Retrieves a researcher from the database based on their email address.

        Args:
            email: The email address to search for.

        Returns:
            The Researcher object if found, otherwise None.
        """
        statement = select(Researcher).where(Researcher.email == email)
        # --- DB CALL: Needs await ---
        result = await self.session.exec(statement) # Corrected: Added await
        researcher = result.first() # Get result
        # --- End DB Call ---
        return researcher

    async def authenticate_researcher(self, email: str, password: str) -> Optional[Researcher]:
        """
        Authenticates a researcher based on email and password.

        Args:
            email: The researcher's email.
            password: The researcher's plain text password.

        Returns:
            The authenticated Researcher object if credentials are valid and
            the researcher is active, otherwise None.
        """
        # This method calls the corrected get_researcher_by_email above
        researcher = await self.get_researcher_by_email(email=email)

        # Check if researcher exists
        if not researcher:
            print(f"Authentication failed: Researcher with email {email} not found.")
            return None

        # Check if researcher is active
        if not researcher.is_active:
            print(f"Authentication failed: Researcher {email} is not active.")
            return None

        # Check if the provided password matches the stored hash
        if not verify_password(password, researcher.hashed_password):
            print(f"Authentication failed: Incorrect password for researcher {email}.")
            return None

        # If all checks pass, return the researcher object
        print(f"Authentication successful for researcher {email}.")
        return researcher

    # --- Optional: Function to Create Researchers ---
    # This would typically be used via a separate admin interface or script,
    # or potentially a protected API endpoint.
    async def create_researcher(self, researcher_data: ResearcherCreate) -> Researcher:
        """
        Creates a new researcher record in the database.

        Args:
            researcher_data: Schema containing email, password, and optional full_name.

        Returns:
            The newly created Researcher object.

        Raises:
            ValueError: If an researcher with the given email already exists.
        """
        # This method calls the corrected get_researcher_by_email above
        existing_researcher = await self.get_researcher_by_email(email=researcher_data.email)
        if existing_researcher:
            raise ValueError(f"Researcher with email {researcher_data.email} already exists.")

        # Hash the password before storing
        hashed_pwd = get_password_hash(researcher_data.password)

        # Create the DB model instance
        db_researcher = Researcher(
            email=researcher_data.email,
            hashed_password=hashed_pwd,
            full_name=researcher_data.full_name,
            is_active=True # Default to active
        )

        self.session.add(db_researcher)
        # flush and refresh were already correctly awaited
        await self.session.flush()
        await self.session.refresh(db_researcher)

        print(f"Created new researcher: {db_researcher.email}")
        return db_researcher
