# _setup_dev_data.py
# Updated to remove static QuizQuestion population. Keeps Researcher population.

import asyncio
import logging
from typing import Dict, List, Any

# Assuming database and models are correctly located relative to this script
# Adjust paths if necessary if running from a different location
try:
    from backend.db.database import AsyncSessionFactory # Import the factory
    from backend.db.models import QuizQuestion, Researcher # Keep Researcher import
    from backend.core.security import get_password_hash # Import password hashing function
except ImportError as e:
    print(f"Error importing backend modules: {e}")
    print("Please ensure this script is run from the project root directory (ai_tutor_experiment)")
    print("And that your environment (`ai_tutor_env`) is activated.")
    exit(1)

# Configure basic logging for the script
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

# --- REMOVED quiz_questions_data list ---
# The list defining static quiz questions, options, answers, IRT params, etc.,
# has been removed as this table is no longer used by the RAG/LLM quiz.
# --- END REMOVED ---


# --- Initial Researcher Data ---
# Keep this section to ensure a default researcher account exists
researcher_data: List[Dict[str, Any]] = [
    {
        "email": "researcher@example.com",
        "password": "password", # Plain text password - will be hashed
        "full_name": "Default Researcher",
        "is_active": True
    }
    # Add more researchers here if needed
]
# --- End Initial Researcher Data ---


async def add_dev_data():
    """Asynchronously adds development data (researchers) to the database."""
    logger.info("Attempting to add development data (Researchers)...")

    async with AsyncSessionFactory() as session:
        try:
            # --- REMOVED QuizQuestion adding logic ---
            # The loop iterating through quiz_questions_data and adding QuizQuestion
            # objects has been removed.
            # --- END REMOVED ---

            # --- Add Researchers ---
            researchers_to_add = []
            logger.info(f"Processing {len(researcher_data)} researcher(s)...")
            for data in researcher_data:
                # Check if researcher already exists
                existing_researcher_stmt = select(Researcher).where(Researcher.email == data["email"])
                result = await session.exec(existing_researcher_stmt)
                existing = result.first()
                if existing:
                    logger.info(f"Researcher with email {data['email']} already exists. Skipping.")
                    continue

                # Hash the password
                hashed_password = get_password_hash(data["password"])
                # Create Researcher object
                new_researcher = Researcher(
                    email=data["email"],
                    hashed_password=hashed_password,
                    full_name=data.get("full_name"),
                    is_active=data.get("is_active", True)
                    # created_at is handled by default factory
                )
                researchers_to_add.append(new_researcher)
                logger.info(f"Prepared researcher: {data['email']}")

            if researchers_to_add:
                session.add_all(researchers_to_add)
                logger.info(f"Added {len(researchers_to_add)} new researcher(s) to session.")
            else:
                logger.info("No new researchers to add.")

            # Commit the changes for researchers
            await session.commit()
            logger.info("Researcher data committed successfully.")

        except ImportError:
            logger.error("Import error occurred. Could not import necessary modules.")
            logger.error("Ensure script is run from project root and environment is active.")
            await session.rollback() # Rollback any potential partial changes
        except Exception as e:
            logger.error(f"An error occurred during data setup: {e}", exc_info=True)
            await session.rollback() # Rollback on error
        finally:
            logger.info("Dev data script finished processing.")


if __name__ == "__main__":
    # Ensure necessary modules are imported before running main
    # (Imports are now at the top with error handling)
    logger.info("Running development data setup script...")
    asyncio.run(add_dev_data())
    logger.info("Script execution complete.")