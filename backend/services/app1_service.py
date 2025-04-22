# ai_tutor_experiment/backend/services/app1_service.py
# RESTORED VERSION with RAG Context (incorporating logging improvements)

import uuid
import os
import logging
from datetime import datetime
from typing import Optional

from sqlmodel import select
from sqlmodel.ext.asyncio.session import AsyncSession
from groq import AsyncGroq, RateLimitError, APIError

# Import relevant models and schemas
from backend.db.models import App1InteractionLog, Consent
from backend.schemas.interaction import App1InteractionLogCreate

# Import settings to access API keys and RAG config
from backend.core.config import settings

# Import RAG components
from backend.rag.retriever import load_vector_store, retrieve_relevant_chunks
from langchain_community.vectorstores import FAISS # For type hinting

# Setup logger
logger = logging.getLogger(__name__)


class App1Service:
    """
    Service layer for handling App1 specific logic,
    including LLM interaction logging, RAG context retrieval, and Groq API calls.
    """

    def __init__(self, session: AsyncSession):
        """
        Initializes the service with an async database session.
        """
        self.session = session
        # Initialize Groq client
        if settings.GROQ_API_KEY:
            self.groq_client = AsyncGroq(api_key=settings.GROQ_API_KEY)
            logger.info("Groq client initialized for App1Service.")
        else:
            self.groq_client = None
            logger.warning("GROQ_API_KEY not found in settings. App1 LLM calls will be disabled.")
        # Embedding model for RAG is loaded within load_vector_store.

    async def log_app1_interaction(
            self,
            session_uuid: uuid.UUID,
            log_data: App1InteractionLogCreate
    ) -> App1InteractionLog:
        """
        Logs a single App1 interaction event (e.g., UserPrompt, LlmResponse)
        to the database.
        """
        consent_check = await self.session.get(Consent, session_uuid)
        if not consent_check:
            logger.error(f"App1 Interaction Log Error: Session with UUID {session_uuid} not found.")
            raise ValueError(f"App1 Interaction Log Error: Session with UUID {session_uuid} not found.")

        # Truncate potentially long text fields for logging if necessary
        # Example: Truncate prompt_text if it includes context
        max_log_len = 1000 # Example max length
        prompt_to_log = log_data.prompt_text
        if log_data.event_type == 'LlmResponse' and prompt_to_log and len(prompt_to_log) > max_log_len:
            prompt_to_log = prompt_to_log[:max_log_len] + "... (truncated)"

        db_log_entry = App1InteractionLog(
            session_uuid=session_uuid,
            event_type=log_data.event_type,
            prompt_text=prompt_to_log, # Use potentially truncated prompt
            response_text=log_data.response_text,
            error_details=log_data.error_details,
            token_count_prompt=log_data.token_count_prompt,
            token_count_response=log_data.token_count_response,
            llm_response_time_ms=log_data.llm_response_time_ms,
            llm_time_to_first_token_ms=log_data.llm_time_to_first_token_ms
        )

        self.session.add(db_log_entry)
        await self.session.flush()
        await self.session.refresh(db_log_entry)

        logger.debug(f"Logged App1 interaction ({log_data.event_type}) for session {session_uuid}")
        return db_log_entry

    async def get_llm_response(
            self,
            session_uuid: uuid.UUID,
            prompt: str,
            model: str = "llama3-70b-8192"
    ) -> str:
        """
        Sends a prompt to the configured Groq LLM, retrieving RAG context first,
        and returns the response.
        """
        if not self.groq_client:
            await self.log_app1_interaction(
                session_uuid,
                App1InteractionLogCreate(event_type="Error", error_details="Groq API key not configured")
            )
            logger.error(f"Groq call attempted for session {session_uuid} but API key is missing.")
            raise ValueError("Groq API key is not configured in settings.")

        # --- RAG Context Retrieval ---
        retrieved_context_str = ""
        vector_store: Optional[FAISS] = None
        assigned_paper_id: Optional[str] = None
        rag_error_details = None
        relevant_chunks = [] # Keep track of retrieved chunks

        try:
            consent = await self.session.get(Consent, session_uuid)
            if not consent:
                logger.error(f"Consent record not found for session {session_uuid} during RAG.")
                raise ValueError(f"Session {session_uuid} not found.")
            if not consent.assigned_paper:
                logger.warning(f"No paper assigned for session {session_uuid}. Proceeding without RAG.")
                rag_error_details = "No paper assigned to session"
            else:
                assigned_paper_id = consent.assigned_paper
                logger.info(f"Session {session_uuid} assigned paper: {assigned_paper_id}. Attempting RAG.")
                try:
                    vector_store = load_vector_store(paper_id=assigned_paper_id)
                    logger.info(f"Vector store loaded successfully for paper '{assigned_paper_id}'.")
                except FileNotFoundError:
                    logger.error(f"Vector store file not found for paper '{assigned_paper_id}'. Processing needed?")
                    rag_error_details = f"Vector store not found for {assigned_paper_id}"
                    vector_store = None
                except Exception as e:
                    logger.error(f"Failed to load vector store for paper '{assigned_paper_id}': {e}", exc_info=True)
                    rag_error_details = f"Error loading vector store for {assigned_paper_id}: {e}"
                    vector_store = None

                if vector_store:
                    try:
                        k = settings.RAG_TOP_K # Use value from config
                        logger.info(f"Retrieving top-{k} chunks for session {session_uuid} query: '{prompt[:50]}...'")
                        relevant_chunks = retrieve_relevant_chunks(query=prompt, vector_store=vector_store, k=k)
                        retrieved_context_str = "\n\n".join(relevant_chunks)
                        logger.info(f"Retrieved {len(relevant_chunks)} chunks for session {session_uuid}.")
                        if not relevant_chunks:
                            logger.warning(f"RAG retrieval returned 0 chunks for query: '{prompt[:50]}...'")
                            rag_error_details = "No relevant chunks found by RAG." # Add specific detail
                    except Exception as e:
                        logger.error(f"Failed to retrieve chunks for session {session_uuid}, paper '{assigned_paper_id}': {e}", exc_info=True)
                        rag_error_details = f"Error retrieving chunks: {e}"
                        retrieved_context_str = ""

        except ValueError as e:
            logger.error(f"ValueError during RAG setup for session {session_uuid}: {e}")
            rag_error_details = f"ValueError: {e}"
        except Exception as e:
            logger.error(f"Unexpected error during RAG setup for session {session_uuid}: {e}", exc_info=True)
            rag_error_details = f"Unexpected RAG setup error: {e}"
        # --- End RAG Context Retrieval ---


        logger.info(f"Sending prompt to Groq for session {session_uuid}. RAG context length: {len(retrieved_context_str)}")
        start_time = datetime.now()

        try:
            # --- CONSTRUCT FINAL PROMPT ---
            messages = []
            # ** Refined System Prompt **
            system_prompt_content = (
                "You are an AI Research Tutor assisting a student learning about a specific research paper.\n"
                "Your goal is to answer the student's questions accurately based *only* on the relevant text snippets "
                "from the paper provided below.\n\n"
                "Instructions:\n"
                "1. Carefully read the user's question.\n"
                "2. Review the following text snippets extracted from the paper:\n"
                "--- START OF RELEVANT PAPER SNIPPETS ---\n\n"
                f"{retrieved_context_str if retrieved_context_str else 'No specific snippets were retrieved for this question.'}\n\n"
                "--- END OF RELEVANT PAPER SNIPPETS ---\n\n"
                "3. Formulate your answer based *strictly* on the information contained within these snippets.\n"
                "4. Do *not* use any external knowledge, general information, or information from other parts of the paper not included in the snippets.\n"
                "5. If the provided snippets do not contain the information needed to answer the question, explicitly state that. For example: "
                "'Based on the provided text snippets, the paper does not seem to contain information about X.' or "
                "'The relevant snippets do not provide details on Y.'\n"
                "6. Be concise and directly answer the question asked."
            )
            messages.append({"role": "system", "content": system_prompt_content})
            # Add user prompt
            messages.append({"role": "user", "content": prompt})
            # --- END PROMPT CONSTRUCTION ---

            # Log the user prompt separately before the call
            await self.log_app1_interaction(
                session_uuid,
                App1InteractionLogCreate(event_type="UserPrompt", prompt_text=prompt)
            )


            chat_completion = await self.groq_client.chat.completions.create(
                messages=messages,
                model=model,
                # temperature=0.3, # Lower temperature for more factual/less creative responses
                # max_tokens=1000, # Set a reasonable max response length
            )

            end_time = datetime.now()
            response_time_ms = int((end_time - start_time).total_seconds() * 1000)

            response_text = chat_completion.choices[0].message.content
            token_prompt = chat_completion.usage.prompt_tokens if chat_completion.usage else None
            token_response = chat_completion.usage.completion_tokens if chat_completion.usage else None

            # Log the successful LLM response, include RAG error if one occurred
            # Log the full prompt text (which includes context) here, but truncated
            log_prompt_text = f"System Prompt w/ Context (len={len(retrieved_context_str)}) + User: {prompt}"

            await self.log_app1_interaction(
                session_uuid,
                App1InteractionLogCreate(
                    event_type="LlmResponse",
                    prompt_text=log_prompt_text, # Log representation of prompt
                    response_text=response_text,
                    error_details=rag_error_details, # Log RAG status/errors here
                    token_count_prompt=token_prompt,
                    token_count_response=token_response,
                    llm_response_time_ms=response_time_ms
                )
            )

            return response_text

        except RateLimitError as e: # Handle specific errors
            logger.error(f"Groq API Rate Limit Error for session {session_uuid}: {e}")
            await self.log_app1_interaction(
                session_uuid,
                App1InteractionLogCreate(event_type="Error", prompt_text=prompt, error_details=f"Groq Rate Limit Error: {e.status_code}. RAG Status: {rag_error_details or 'OK'}")
            )
            raise APIError(f"Rate limit exceeded. Please try again later. Status: {e.status_code}", request=e.request, body=e.body) from e
        except APIError as e:
            logger.error(f"Groq API Error for session {session_uuid}: {e}")
            await self.log_app1_interaction(
                session_uuid,
                App1InteractionLogCreate(event_type="Error", prompt_text=prompt, error_details=f"Groq API Error: {e.status_code} - {e.message}. RAG Status: {rag_error_details or 'OK'}")
            )
            raise e
        except Exception as e: # Catch-all for other unexpected errors
            logger.error(f"Unexpected error calling Groq API for session {session_uuid}: {e}", exc_info=True)
            await self.log_app1_interaction(
                session_uuid,
                App1InteractionLogCreate(event_type="Error", prompt_text=prompt, error_details=f"Unexpected LLM error: {str(e)}. RAG Status: {rag_error_details or 'OK'}")
            )
            raise APIError(f"An unexpected error occurred contacting the LLM service: {str(e)}", request=None, body=None) from e