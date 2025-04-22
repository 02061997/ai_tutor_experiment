# backend/llm/client.py
import asyncio

import google.generativeai as genai
import logging
import time

from backend.core.config import settings # Import settings for API key

logger = logging.getLogger(__name__)

# Configure the Gemini client globally (or within a function if preferred)
try:
    genai.configure(api_key=settings.GOOGLE_API_KEY)
    logger.info("Google Generative AI client configured.")
except Exception as e:
    logger.error(f"Failed to configure Google Generative AI client: {e}", exc_info=True)
    # Depending on requirements, you might raise an error here or handle it downstream

# Define generation configuration (optional, adjust as needed)
generation_config = {
  "temperature": 0.7, # Adjust for creativity vs predictability
  "top_p": 1.0,
  "top_k": 32, # Example values
  "max_output_tokens": 1024, # Adjust based on expected output length
}

# Define safety settings (adjust based on needs and model documentation)
safety_settings = [
    {"category": "HARM_CATEGORY_HARASSMENT", "threshold": "BLOCK_MEDIUM_AND_ABOVE"},
    {"category": "HARM_CATEGORY_HATE_SPEECH", "threshold": "BLOCK_MEDIUM_AND_ABOVE"},
    {"category": "HARM_CATEGORY_SEXUALLY_EXPLICIT", "threshold": "BLOCK_MEDIUM_AND_ABOVE"},
    {"category": "HARM_CATEGORY_DANGEROUS_CONTENT", "threshold": "BLOCK_MEDIUM_AND_ABOVE"},
]

async def ask_gemini(prompt: str, model_name: str = "gemini-1.5-flash-latest") -> str:
    """
    Sends a prompt to the specified Gemini model and returns the text response.
    Includes basic error handling and retry logic.
    """
    logger.debug(f"Sending prompt to Gemini model '{model_name}':\n{prompt[:200]}...") # Log truncated prompt
    retries = 3
    delay = 2 # seconds
    for attempt in range(retries):
        try:
            model = genai.GenerativeModel(
                model_name=model_name,
                generation_config=generation_config,
                safety_settings=safety_settings
            )
            response = await model.generate_content_async(prompt) # Use async version

            # Handle potential blocks or empty responses
            if not response.candidates:
                 logger.warning(f"Gemini response blocked or empty. Reason: {response.prompt_feedback}")
                 # Consider returning a specific error message or None
                 return "(Response blocked or empty)"

            # Extract text, handling potential errors
            try:
                 response_text = response.text
                 logger.debug(f"Received Gemini response (length {len(response_text)}): {response_text[:200]}...")
                 return response_text
            except ValueError as ve:
                 logger.warning(f"Could not extract text from Gemini response candidate. Details: {ve}. Candidate: {response.candidates[0]}")
                 return "(Failed to extract text from response)"

        except Exception as e:
            logger.error(f"Error calling Gemini API (Attempt {attempt + 1}/{retries}): {e}", exc_info=True)
            if attempt < retries - 1:
                logger.info(f"Retrying Gemini call in {delay} seconds...")
                await asyncio.sleep(delay) # Use asyncio.sleep for async
                delay *= 2 # Exponential backoff
            else:
                logger.error("Max retries reached for Gemini API call.")
                # Raise the error or return a specific error message
                raise RuntimeError("Failed to get response from Gemini after multiple retries") from e
    # Should not be reached if retries are handled correctly, but as a fallback:
    raise RuntimeError("Gemini call failed unexpectedly after retries.")