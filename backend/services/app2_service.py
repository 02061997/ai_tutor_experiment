# backend/services/app2_service.py

import uuid
import os
from typing import Optional

# Import the Google AI Gemini library
import google.generativeai as genai

# Import settings to access API keys
from backend.core.config import settings

# --- Configuration ---
# Model name - Use a recent, appropriate model like flash for speed/cost or pro for higher quality
GEMINI_MODEL_NAME = "gemini-1.5-flash-latest"

class App2Service:
    """
    Service layer for handling App2 specific logic,
    including generating summaries using Google AI Gemini.
    """

    def __init__(self):
        """
        Initializes the service and configures the Google AI client.
        """
        self.gemini_model = None
        if settings.GOOGLE_API_KEY:
            try:
                # Configure the library with the API key from settings
                genai.configure(api_key=settings.GOOGLE_API_KEY)
                # Create a generative model instance
                self.gemini_model = genai.GenerativeModel(GEMINI_MODEL_NAME)
                print(f"DEBUG: Google AI Gemini client initialized with model {GEMINI_MODEL_NAME}.")
            except Exception as e:
                # Catch potential configuration errors
                print(f"ERROR: Failed to configure Google AI Gemini client: {e}")
                self.gemini_model = None
        else:
            print("Warning: GOOGLE_API_KEY not found in settings. App2 summary generation will be disabled.")

    async def generate_summary(
        self,
        text_to_summarize: str,
        # Optional: Add session_uuid if logging is needed
        # session_uuid: Optional[uuid.UUID] = None
    ) -> str:
        """
        Generates a summary for the given text using the configured Gemini model.

        Args:
            text_to_summarize: The text content (e.g., from the research paper) to summarize.
            session_uuid: Optional session ID for potential logging (not implemented yet).

        Returns:
            The generated summary text as a string.

        Raises:
            ValueError: If the Google AI API key/client is not configured.
            Exception: If the API call to Gemini fails.
        """
        # Check if the client was initialized successfully
        if not self.gemini_model:
            # TODO: Optionally log this failure as an App2 interaction/error event
            raise ValueError("Google AI Gemini client is not configured (API key missing or invalid).")

        # Construct a prompt for summarization
        # Keep it relatively simple for now, can be refined
        prompt = f"""Please provide a concise summary of the key points, findings, and conclusions presented in the following text:

        --- TEXT START ---
        {text_to_summarize}
        --- TEXT END ---

        Summary:"""

        print(f"DEBUG: Sending request to Gemini model {GEMINI_MODEL_NAME} for summarization...")

        try:
            # Use generate_content_async for asynchronous operation
            response = await self.gemini_model.generate_content_async(prompt)

            # TODO: Add more robust error checking based on response structure/safety ratings if needed
            # Check response.prompt_feedback for blocked prompts etc.

            # Extract the generated text
            summary_text = response.text
            print(f"DEBUG: Received summary from Gemini.")

            # TODO: Log the successful summary generation event if needed

            return summary_text

        except Exception as e:
            # Catch potential API errors or other issues during generation
            print(f"ERROR: Failed to generate summary using Gemini: {e}")
            # TODO: Log the error event if needed
            # Re-raise the exception to be handled by the API endpoint
            raise Exception(f"Failed to generate summary from the AI service: {str(e)}") from e

    # --- Placeholder for other App2 specific service methods ---
    # e.g., fetching recommendations based on quiz results
    # async def get_recommendations(self, session_uuid: uuid.UUID, attempt_id: uuid.UUID) -> List[str]: ...

