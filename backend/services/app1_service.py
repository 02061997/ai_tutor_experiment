# ai_tutor_experiment/backend/services/app1_service.py
# Updated with Groq LLM call

import uuid
import os # Import os
from datetime import datetime
from typing import Optional

from sqlmodel import select
from sqlmodel.ext.asyncio.session import AsyncSession
from groq import Groq, AsyncGroq, RateLimitError, APIError # Import Groq library components

# Import relevant models and schemas
from backend.db.models import App1InteractionLog, Consent
from backend.schemas.interaction import App1InteractionLogCreate

# Import settings to access API keys
from backend.core.config import settings


class App1Service:
    """
    Service layer for handling App1 specific logic,
    including LLM interaction logging and Groq API calls.
    """

    def __init__(self, session: AsyncSession):
        """
        Initializes the service with an async database session.

        Args:
            session: The database session dependency.
        """
        self.session = session
        # Initialize Groq client (consider initializing once if service is singleton)
        # Use AsyncGroq for async FastAPI methods
        if settings.GROQ_API_KEY:
            self.groq_client = AsyncGroq(api_key=settings.GROQ_API_KEY)
            print("DEBUG: Groq client initialized.")
        else:
            self.groq_client = None
            print("Warning: GROQ_API_KEY not found in settings. App1 LLM calls will be disabled.")

    async def log_app1_interaction(
        self,
        session_uuid: uuid.UUID,
        log_data: App1InteractionLogCreate
    ) -> App1InteractionLog:
        """
        Logs a single App1 interaction event (e.g., UserPrompt, LlmResponse)
        to the database.

        Args:
            session_uuid: The UUID of the session the interaction belongs to.
            log_data: The schema containing the details of the interaction event.

        Returns:
            The created App1InteractionLog database object.

        Raises:
            ValueError: If the associated session_uuid does not exist.
        """
        # Optional: Verify session_uuid exists
        consent_check = await self.session.get(Consent, session_uuid)
        if not consent_check:
             raise ValueError(f"App1 Interaction Log Error: Session with UUID {session_uuid} not found.")

        db_log_entry = App1InteractionLog(
            session_uuid=session_uuid,
            event_type=log_data.event_type,
            prompt_text=log_data.prompt_text,
            response_text=log_data.response_text,
            error_details=log_data.error_details,
            token_count_prompt=log_data.token_count_prompt,
            token_count_response=log_data.token_count_response,
            llm_response_time_ms=log_data.llm_response_time_ms,
            llm_time_to_first_token_ms=log_data.llm_time_to_first_token_ms
            # log_id and log_timestamp have defaults
        )

        self.session.add(db_log_entry)
        await self.session.flush()
        await self.session.refresh(db_log_entry)

        print(f"Logged App1 interaction ({log_data.event_type}) for session {session_uuid}")
        return db_log_entry

    async def get_llm_response(
        self,
        session_uuid: uuid.UUID, # Include session for potential context/history later
        prompt: str,
        model: str = "llama3-70b-8192" # Default to Llama 3 70B as per plan
    ) -> str:
        """
        Sends a prompt to the configured Groq LLM and returns the response.

        Args:
            session_uuid: The session ID (for logging context).
            prompt: The user's input prompt.
            model: The Groq model to use.

        Returns:
            The text content of the LLM's response.

        Raises:
            ValueError: If Groq API key is not configured.
            APIError: If there's an issue communicating with the Groq API.
        """
        if not self.groq_client:
            # Log this event as an error
            await self.log_app1_interaction(
                session_uuid,
                App1InteractionLogCreate(event_type="Error", error_details="Groq API key not configured")
            )
            raise ValueError("Groq API key is not configured in settings.")

        print(f"Sending prompt to Groq for session {session_uuid}...")
        start_time = datetime.now()

        try:
            # Construct messages list (can be expanded later to include chat history)
            messages = [
                # Optional: Add a system prompt here if desired
                # {"role": "system", "content": "You are a helpful assistant."},
                {"role": "user", "content": prompt}
            ]

            chat_completion = await self.groq_client.chat.completions.create(
                messages=messages,
                model=model,
                # Optional parameters:
                # temperature=0.7,
                # max_tokens=1024,
                # top_p=1,
                # stop=None,
                # stream=False, # Set to True for streaming responses
            )

            end_time = datetime.now()
            response_time_ms = int((end_time - start_time).total_seconds() * 1000)

            # Extract response text
            response_text = chat_completion.choices[0].message.content

            # Extract usage data (if available and needed)
            token_prompt = chat_completion.usage.prompt_tokens if chat_completion.usage else None
            token_response = chat_completion.usage.completion_tokens if chat_completion.usage else None

            # Log the successful LLM response interaction
            await self.log_app1_interaction(
                session_uuid,
                App1InteractionLogCreate(
                    event_type="LlmResponse",
                    prompt_text=prompt, # Log the prompt that led to this response
                    response_text=response_text,
                    token_count_prompt=token_prompt,
                    token_count_response=token_response,
                    llm_response_time_ms=response_time_ms
                    # TODO: Add time_to_first_token if using streaming
                )
            )

            return response_text

        except RateLimitError as e:
            print(f"Groq API Rate Limit Error: {e}")
            await self.log_app1_interaction(
                session_uuid,
                App1InteractionLogCreate(event_type="Error", prompt_text=prompt, error_details=f"Groq Rate Limit Error: {e.status_code}")
            )
            raise APIError(f"Rate limit exceeded. Please try again later. Status: {e.status_code}", request=e.request, body=e.body) from e
        except APIError as e:
            print(f"Groq API Error: {e}")
            await self.log_app1_interaction(
                session_uuid,
                App1InteractionLogCreate(event_type="Error", prompt_text=prompt, error_details=f"Groq API Error: {e.status_code} - {e.message}")
            )
            # Re-raise to be handled by the endpoint
            raise e
        except Exception as e:
             # Catch any other unexpected errors
             print(f"Unexpected error calling Groq API: {e}")
             await self.log_app1_interaction(
                session_uuid,
                App1InteractionLogCreate(event_type="Error", prompt_text=prompt, error_details=f"Unexpected error: {str(e)}")
             )
             raise APIError(f"An unexpected error occurred contacting the LLM service: {str(e)}", request=None, body=None) from e

