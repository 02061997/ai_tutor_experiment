# backend/services/app2_service.py

import uuid
import os
import json
import re
import traceback
from typing import Optional, List, Dict, Any

# Import settings, RAG, and the CORRECT LLM function
from backend.core.config import settings
from backend.rag.retriever import retrieve_relevant_chunks, load_vector_store
# --- CORRECTED IMPORT ---
from backend.llm.client import ask_gemini # Import ask_gemini
# ------------------------

# Helper: clean_llm_response (remains the same)
def clean_llm_response(text: str) -> str:
    # ... (keep the existing clean_llm_response function) ...
    if not isinstance(text, str):
        print(f"Warning: clean_llm_response received non-string: {type(text)}")
        return "(Invalid content type)"
    patterns_to_remove = [
        r"^\s*okay,?\s*here'?s the summary.*\n+",
        r"^\s*based on the provided text excerpt[:,]?\s*",
        r"\n*\s*let me know if you need further clarification.*$",
        r"\n*\s*i hope this summary is helpful.*$",
        r"^\s*summary:\s*",
        r"^\s*\*\*\s*[A-Za-z ]+\s*\*\*\s*\n*",
        r"^\s*[\*\-]\s*$",
        r"^\s*$",
    ]
    cleaned_text = text
    for pattern in patterns_to_remove:
        cleaned_text = re.sub(pattern, "", cleaned_text, flags=re.IGNORECASE | re.MULTILINE).strip()
    return cleaned_text if cleaned_text else "(Empty response after cleaning)"


class App2Service:
    """
    Service layer for handling App2 specific logic,
    including generating STRUCTURED summaries using Google AI Gemini and RAG.
    """

    def __init__(self):
        """
        Initializes the service. No model initialization needed here anymore,
        as ask_gemini handles it.
        """
        # --- REMOVE self.gemini_model initialization ---
        print("DEBUG [App2Service]: Initialized.")
        # ---------------------------------------------

    async def _generate_section_content(
            self,
            paper_id: str,
            vector_store: Any,
            query: str,
            prompt_template: str,
            k: int = 3
    ) -> str:
        """Helper to retrieve context and generate content for one section/sub-point."""
        print(f"--- Generating content for query: '{query}' (k={k}) ---")
        try:
            # 1. Retrieve relevant chunks (remains the same)
            retrieved_chunks = retrieve_relevant_chunks(query, vector_store, k=k)
            # ... (rest of context prep remains the same) ...
            if not retrieved_chunks:
                print(f"Warning: No relevant chunks found for query: {query}")
                return "(No relevant information found in paper)"
            context_excerpt = "\n\n---\n\n".join(retrieved_chunks)
            MAX_CONTEXT_LEN = 10000
            if len(context_excerpt) > MAX_CONTEXT_LEN:
                print(f"Warning: Truncating context excerpt for query '{query}' from {len(context_excerpt)} to {MAX_CONTEXT_LEN}")
                context_excerpt = context_excerpt[:MAX_CONTEXT_LEN] + "... (truncated)"

            # 3. Prepare the prompt (remains the same)
            prompt = prompt_template.format(excerpt=context_excerpt)

            # --- CORRECTED LLM Call ---
            # 4. Call the imported ask_gemini function
            print(f"DEBUG: Calling ask_gemini for query '{query}'...")
            response_text = await ask_gemini(prompt) # Pass the prompt
            # -------------------------

            # 5. Clean and return the response
            # Assuming ask_gemini returns the text directly or handles errors internally
            cleaned_response = clean_llm_response(response_text)
            print(f"DEBUG: Received and cleaned response for query '{query}'.")
            return cleaned_response

        except Exception as e:
            print(f"ERROR generating content for query '{query}': {e}")
            traceback.print_exc()
            return f"(Error generating content: {str(e)})"


    async def generate_structured_summary(
            self,
            paper_id: str
    ) -> List[Dict[str, Any]]:
        """Generates a structured summary using multi-step RAG and prompting."""
        # --- REMOVED Check for self.gemini_model ---

        # --- Define Summary Structure (remains the same) ---
        summary_structure = [
            # ... (keep the existing structure definition) ...
            {
                "section_title": "Introduction",
                "sub_points": [
                    {"title": "Focus", "query": "Main topic, subject, focus of the paper", "k": 3,
                     "prompt_template": "Based ONLY on the following text excerpt, what is the main focus or subject the paper investigates? Answer in one concise sentence. DO NOT add intro/outro phrases.\nExcerpt:\n{excerpt}\n\nFocus:"},
                    {"title": "Importance", "query": "Problem importance, significance, relevance", "k": 4,
                     "prompt_template": "Based ONLY on the following text excerpt, why is the topic/problem important or relevant? Answer concisely (1-2 sentences). DO NOT add intro/outro phrases.\nExcerpt:\n{excerpt}\n\nImportance:"},
                    {"title": "Research Questions/Hypotheses", "query": "Research questions, hypotheses tested", "k": 4,
                     "prompt_template": "Based ONLY on the text excerpt, list the specific research questions OR hypotheses studied. Use a numbered list (1., 2., ...). If none explicitly stated, write 'None stated'. DO NOT add intro/outro phrases.\nExcerpt:\n{excerpt}\n\nQuestions/Hypotheses:"},
                    {"title": "Key Contribution/Finding", "query": "Main contribution, primary outcome, key finding", "k": 4,
                     "prompt_template": "Based ONLY on the text excerpt, what is the single main contribution or key finding mentioned? Answer concisely in one sentence. DO NOT add intro/outro phrases.\nExcerpt:\n{excerpt}\n\nKey Contribution/Finding:"}
                ]
            },
            {
                "section_title": "Background & Related Work", "k": 5,
                "query": "Related work, literature review, background context",
                "prompt_template": "Based ONLY on the provided text excerpt, concisely summarize the main points discussed regarding background or related work in 2-4 bullet points (-). DO NOT add intro/outro phrases.\nExcerpt:\n{excerpt}\n\nBackground Summary Points:"
            },
            {
                "section_title": "Methodology", "k": 5,
                "query": "Methodology, methods, experimental setup, procedure, dataset, participants",
                "prompt_template": "Based ONLY on the provided text excerpt, concisely summarize the key aspects of the methodology (like task, participants, procedure, tools/datasets used) in 3-5 bullet points (-). DO NOT add intro/outro phrases.\nExcerpt:\n{excerpt}\n\nMethodology Key Aspects:"
            },
            {
                "section_title": "Results", "k": 5,
                "query": "Results, findings, key outcomes, analysis results",
                "prompt_template": "Based ONLY on the provided text excerpt, concisely summarize the main results or findings reported in 3-5 bullet points (-). DO NOT add intro/outro phrases.\nExcerpt:\n{excerpt}\n\nResults Summary Points:"
            },
            {
                "section_title": "Discussion", "k": 5,
                "query": "Discussion, interpretation of results, implications, limitations",
                "prompt_template": "Based ONLY on the provided text excerpt, concisely summarize the main points of the discussion (interpretation, implications, limitations) in 2-4 bullet points (-). DO NOT add intro/outro phrases.\nExcerpt:\n{excerpt}\n\nDiscussion Points:"
            },
            {
                "section_title": "Conclusion", "k": 4,
                "query": "Conclusion, concluding remarks, final takeaway, future work",
                "prompt_template": "Based ONLY on the text excerpt:\n- State the main conclusion/takeaway in one sentence.\n- List future work mentioned (if any) in bullet points (-).\nDO NOT add intro/outro phrases.\nExcerpt:\n{excerpt}\n\nConclusion & Future Work:"
            }
        ]
        # ----------------------------------------------------

        structured_summary_output = []

        try:
            # --- Load Vector Store (remains the same) ---
            print(f"Loading vector store for paper_id: {paper_id}")
            vector_store = load_vector_store(paper_id)
            if not vector_store:
                raise ValueError(f"Failed to load vector store for paper {paper_id}.")
            print(f"Vector store loaded successfully for {paper_id}.")

            # --- Loop through structure (calls _generate_section_content) ---
            # This part remains the same, as the helper function now uses ask_gemini
            for section_config in summary_structure:
                # ... (loop logic remains the same) ...
                section_title = section_config["section_title"]
                print(f"--- Processing Section: {section_title} ---")
                section_data: Dict[str, Any] = {"title": section_title}

                if "sub_points" in section_config:
                    content_dict = {}
                    for sub_point_config in section_config["sub_points"]:
                        sub_title = sub_point_config["title"]
                        content_dict[sub_title] = await self._generate_section_content(
                            paper_id=paper_id,
                            vector_store=vector_store,
                            query=sub_point_config["query"],
                            prompt_template=sub_point_config["prompt_template"],
                            k=sub_point_config.get("k", 3)
                        )
                    section_data["content"] = content_dict
                else:
                    section_data["content"] = await self._generate_section_content(
                        paper_id=paper_id,
                        vector_store=vector_store,
                        query=section_config["query"],
                        prompt_template=section_config["prompt_template"],
                        k=section_config.get("k", 5)
                    )
                structured_summary_output.append(section_data)
                print(f"--- Finished Section: {section_title} ---")


        except FileNotFoundError as e:
            print(f"ERROR: Vector store not found for paper {paper_id}. Cannot generate summary. {e}")
            raise ValueError(f"Summary generation failed: Prerequisite vector store for paper '{paper_id}' not found.") from e
        except Exception as e:
            print(f"ERROR during structured summary generation loop: {e}")
            traceback.print_exc()
            raise Exception("An error occurred during structured summary generation.") from e

        print(f"Finished generating structured summary for paper {paper_id}.")
        return structured_summary_output

    # Remove or comment out the old generate_simple_summary if no longer needed
    # async def generate_simple_summary(self, text_to_summarize: str) -> str: ...