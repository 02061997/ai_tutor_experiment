# backend/services/llm_quiz_service.py

import uuid
import json
import random
import re
import traceback
import asyncio
import os
from typing import List, Optional, Dict, Tuple, Any, Coroutine
from datetime import datetime, timezone

from sqlmodel import select, func   # func is used in the mastery query

from sqlmodel.ext.asyncio.session import AsyncSession

from backend.db.models import Consent, GeneratedMCQ, MCQAttempt
from backend.schemas.quiz import (
    GeneratedMCQForParticipant,
    GeneratedMCQAnswerFeedback,
    GeneratedMCQAnswerInput,
)
from backend.rag.retriever import retrieve_relevant_chunks, load_vector_store
from backend.llm.client import ask_gemini
from backend.core.config import settings

# Helper: Clean LLM Response
def clean_llm_response(text: str) -> str:
    """Removes common unwanted conversational phrases and trims whitespace."""
    if not isinstance(text, str):
        print(f"Warning: clean_llm_response received non-string: {type(text)}")
        return "(Invalid content type)"
    patterns_to_remove = [
        r"^\s*okay,?\s*here'?s the quiz question.*\n+",
        r"^\s*based on the provided text excerpt[:,]?\s*",
        r"\n*\s*let me know if you have more questions.*$",
        r"^\s*question:\s*", r"^\s*correct answer:\s*", r"^\s*distractor \d:\s*", r"^\s*explanation:\s*",
        r"^\s*[a-d]\)\s*", # Remove leading option letters like a)
        r"^\s*[\*\-]\s*$",
        r"^\s*$",
    ]
    cleaned_text = text
    for pattern in patterns_to_remove:
        cleaned_text = re.sub(pattern, "", cleaned_text, flags=re.IGNORECASE | re.MULTILINE).strip()
    return cleaned_text if cleaned_text else "(Empty response after cleaning)"

# Helper: Parse Answer/Distractors
def parse_answers_distractors(text: str) -> Tuple[Optional[str], List[str]]:
    """Parses LLM output for Correct Answer and Distractors."""
    correct_answer = None; distractors = []
    lines = [line.strip() for line in text.split('\n') if line.strip()]
    for line in lines:
        if line.lower().startswith("correct answer:"): correct_answer = line.split(":", 1)[1].strip()
        elif line.lower().startswith("distractor 1:"): distractors.append(line.split(":", 1)[1].strip())
        elif line.lower().startswith("distractor 2:"): distractors.append(line.split(":", 1)[1].strip())
        elif line.lower().startswith("distractor 3:"): distractors.append(line.split(":", 1)[1].strip())
    return correct_answer, distractors


class LLMQuizService:
    """
    Service for generating MCQs using LLMs and RAG,
    and managing quiz attempts with mastery tracking.
    """
    def __init__(self, session: AsyncSession):
        self.session = session
        print("DEBUG [LLMQuizService]: Initialized.")


    async def _get_paper_details(self, session_id: uuid.UUID) -> Tuple[str, str, uuid.UUID]:
        """
        Fetches the assigned paper ID, PDF path, and participant_uuid using the session_id.
        """
        print(f"DEBUG [_get_paper_details]: Looking up consent for session_id: {session_id}")
        consent_stmt = select(Consent).where(Consent.session_uuid == session_id)
        consent_result = await self.session.exec(consent_stmt); consent_record = consent_result.first()
        if not consent_record: raise ValueError(f"Session not found for ID: {session_id}")
        if not consent_record.assigned_paper: raise ValueError(f"Session {session_id} has no assigned paper.")
        if not consent_record.participant_uuid: raise ValueError(f"Session {session_id} is missing participant UUID.")
        paper_id = consent_record.assigned_paper; participant_uuid = consent_record.participant_uuid
        PAPER_FILE_MAP = {"Paper1": "./static/pdfs/chapter1.pdf", "Paper2": "./static/pdfs/chapter2.pdf"} # TODO: Centralize
        pdf_path = PAPER_FILE_MAP.get(paper_id)
        if not pdf_path or not os.path.exists(pdf_path): raise FileNotFoundError(f"PDF file for paper '{paper_id}' not found on server.")
        print(f"DEBUG [_get_paper_details]: Found paper '{paper_id}', participant '{participant_uuid}' for session '{session_id}'")
        return paper_id, pdf_path, participant_uuid


    async def _generate_new_mcq(
            self,
            session_id: uuid.UUID, # Added session_id parameter
            paper_id: str,
            vector_store: Any
    ) -> Optional[GeneratedMCQ]:
        """Generates a new MCQ using the multi-step RAG approach."""
        print(f"--- Generating new MCQ for paper {paper_id} (session: {session_id}) ---")
        try:
            # 1. Get Context
            possible_queries = ["key concepts or definitions", "main methodology", "significant results", "discussion points", "conclusion"]; generation_query = random.choice(possible_queries)
            print(f"Using RAG query: '{generation_query}'"); context_chunks = retrieve_relevant_chunks(generation_query, vector_store, k=4)
            if not context_chunks: raise ValueError(f"Failed to retrieve context for query '{generation_query}'.")
            context_excerpt = "\n\n---\n\n".join(context_chunks); MAX_CONTEXT_LEN = 10000
            if len(context_excerpt) > MAX_CONTEXT_LEN: context_excerpt = context_excerpt[:MAX_CONTEXT_LEN] + "...(truncated)"
            print(f"Context excerpt length: {len(context_excerpt)}")

            # 2. Generate Question Text
            prompt_q = f"Based ONLY on the following text excerpt, generate ONE clear multiple-choice question testing understanding of a key point.\nOutput ONLY the question text.\n\nExcerpt:\n{context_excerpt}\n\nQuestion Text Only:"; print("DEBUG: Calling ask_gemini for Question Text...")
            response_q_text = await ask_gemini(prompt_q); question_text = clean_llm_response(response_q_text)
            if not question_text or question_text.startswith("("): raise ValueError(f"LLM failed question text generation. Response: {response_q_text}")
            print(f"Generated Question Text: {question_text}")

            # 3. Generate Correct Answer & Distractors
            prompt_a = f"Excerpt:\n{context_excerpt}\n\nQuestion:\n{question_text}\n\nBased ONLY on the excerpt, provide the single best CORRECT answer. Then, provide exactly THREE plausible but INCORRECT options (distractors).\nFormat EXACTLY:\nCorrect Answer: [The correct answer text]\nDistractor 1: [Incorrect option 1 text]\nDistractor 2: [Incorrect option 2 text]\nDistractor 3: [Incorrect option 3 text]"
            print("DEBUG: Calling ask_gemini for Correct Answer & Distractors..."); response_a_text = await ask_gemini(prompt_a)
            correct_answer_text, distractors = parse_answers_distractors(response_a_text)
            if not correct_answer_text or len(distractors) != 3: print(f"ERROR: Failed parsing answers/distractors. Raw: {response_a_text}"); raise ValueError("LLM failed to provide answers/distractors in the expected format.")
            print(f"Generated Correct Answer: {correct_answer_text}"); print(f"Generated Distractors: {distractors}")

            # 4. Generate Explanation
            prompt_e = f"""Based ONLY on the text excerpt, explain concisely (1-2 sentences) why "{correct_answer_text}" is the correct answer to the question: "{question_text}".\nOutput ONLY the explanation text.\n\nExcerpt:\n{context_excerpt}\n\nExplanation Text Only:"""
            print("DEBUG: Calling ask_gemini for Explanation..."); response_e_text = await ask_gemini(prompt_e)
            explanation = clean_llm_response(response_e_text)
            if explanation.startswith("("): explanation = "No specific explanation could be generated."
            print(f"Generated Explanation: {explanation}")

            # 5. Combine, Shuffle Options, Determine Correct Letter
            all_options = [correct_answer_text] + distractors; random.shuffle(all_options)
            if len(all_options) != 4 or not all(opt for opt in all_options): raise ValueError("Generated options are invalid (missing or empty).")
            try: correct_letter = chr(65 + all_options.index(correct_answer_text))
            except ValueError: raise ValueError("Correct answer text not found in the shuffled options list.")

            # 6. Create and Save DB Model instance including session_uuid
            new_mcq = GeneratedMCQ(
                session_uuid=session_id, # Assign session_id here
                paper_id=paper_id,
                question_text=question_text, # Use correct field name question_text
                option_a=all_options[0], option_b=all_options[1],
                option_c=all_options[2], option_d=all_options[3],
                correct_answer_letter=correct_letter, # Use correct field name correct_answer_letter
                explanation=explanation,
                generation_timestamp=datetime.now(timezone.utc)
            )
            self.session.add(new_mcq); await self.session.commit(); await self.session.refresh(new_mcq)
            print(f"Generated and saved new MCQ ID: {new_mcq.mcq_id} for session {session_id}")
            return new_mcq

        except Exception as e:
            print(f"ERROR during multi-step MCQ generation: {e}")
            traceback.print_exc()
            await self.session.rollback()
            return None


    async def get_next_question(self, session_id: uuid.UUID) -> Optional[GeneratedMCQForParticipant]:
        """
        Selects the next MCQ for the participant based on mastery,
        or generates a new one if necessary.
        Returns a schema object, potentially indicating completion/error.
        """
        try:
            # 1) Get paper/session info
            paper_id, pdf_path, participant_uuid = await self._get_paper_details(session_id)

            # 2) Fetch all MCQs for this paper
            stmt_all = select(GeneratedMCQ).where(GeneratedMCQ.paper_id == paper_id)
            all_paper_mcqs = (await self.session.exec(stmt_all)).all()

            all_paper_mcqs = [m for m in all_paper_mcqs if m.question_text]
            if not all_paper_mcqs:
                print("No valid MCQs (question_text present) – forcing generation.")
            all_ids = {m.mcq_id for m in all_paper_mcqs}
            # 3) Fetch this session's past attempts
            stmt_att = select(MCQAttempt).where(MCQAttempt.session_uuid == session_id)
            attempts = (await self.session.exec(stmt_att)).all()

            # 4) Build mastered / incorrect / attempted sets
            mastered, incorrect, attempted = set(), set(), set()
            mcq_by_id = {m.mcq_id: m for m in all_paper_mcqs}
            for att in attempts:
                if att.mcq_id in mcq_by_id:
                    attempted.add(att.mcq_id)
                    if att.is_correct:
                        mastered.add(att.mcq_id)
                        incorrect.discard(att.mcq_id)
                    else:
                        if att.mcq_id not in mastered:
                            incorrect.add(att.mcq_id)

            unmastered = all_ids - mastered
            retry_ids = incorrect
            unseen = unmastered - attempted

            print(
                f"DEBUG Quiz Selection: Paper={paper_id}, "
                f"All={len(all_ids)}, Attempted={len(attempted)}, "
                f"Mastered={len(mastered)}, Incorrect={len(incorrect)}"
            )

            # 5) Try to pick an existing MCQ
            selected_id = None
            if retry_ids:
                selected_id = random.choice(list(retry_ids))
                print(f"Selected MCQ {selected_id} to retry.")
            elif unseen:
                selected_id = random.choice(list(unseen))
                print(f"Selected unseen/unmastered MCQ {selected_id}.")
            elif unmastered:
                selected_id = random.choice(list(unmastered))
                print(f"Selected previously seen but unmastered MCQ {selected_id}.")
            else:
                print(f"No unmastered questions left for paper {paper_id}.")

            # 6) If none selected, attempt to generate a new one
            if selected_id is None:
                # only generate if we still have room to ask questions
                if unmastered or not all_ids:
                    print("Attempting to generate a new MCQ via RAG/LLM…")
                    try:
                        vs = load_vector_store(paper_id)
                        new_mcq = await self._generate_new_mcq(session_id, paper_id, vs)
                        if new_mcq:
                            selected_id = new_mcq.mcq_id
                            mcq_by_id[selected_id] = new_mcq
                            print(f"Successfully generated MCQ {selected_id}.")
                        else:
                            print("MCQ generation returned None.")
                    except FileNotFoundError:
                        print(f"ERROR: Vector store missing for paper {paper_id}")
                    except Exception as e:
                        print(f"ERROR generating MCQ: {e}")
                        traceback.print_exc()
                # if still nothing, we're done
                if selected_id is None:
                    return GeneratedMCQForParticipant(
                        quiz_complete=True,
                        error="No questions available or generation failed."
                    )

            # 7) Finally, prepare the selected question
            final_mcq = mcq_by_id.get(selected_id)
            if not final_mcq:
                return GeneratedMCQForParticipant(
                    quiz_complete=True,
                    error="Internal error selecting question."
                )

            options = [
                final_mcq.option_a,
                final_mcq.option_b,
                final_mcq.option_c,
                final_mcq.option_d,
            ]
            result = GeneratedMCQForParticipant(
                mcq_id=final_mcq.mcq_id,
                question=final_mcq.question_text,
                options=options,
                quiz_complete=False
            )
            print("🔍 FINAL JSON to return:", result.model_dump(by_alias=True))
            return result

        except Exception as e:
            traceback.print_exc()
            return GeneratedMCQForParticipant(
                quiz_complete=True,
                error=f"Internal server error: {e}"
            )

# ----------------------------------------------------

        except ValueError as e: print(f"ERROR in get_next_question for session {session_id}: {e}"); traceback.print_exc(); return GeneratedMCQForParticipant(quiz_complete=True, error=str(e))
        except Exception as e: print(f"ERROR in get_next_question for session {session_id}: {e}"); traceback.print_exc(); return GeneratedMCQForParticipant(quiz_complete=True, error=f"Internal server error: {e}")


    async def submit_answer(
            self,
            session_id: uuid.UUID,
            request_data: GeneratedMCQAnswerInput
    ) -> GeneratedMCQAnswerFeedback:
        """Checks answer, records attempt using session_id, returns feedback."""
        mcq_id = request_data.mcq_id; chosen_answer_letter = request_data.chosen_answer_letter.upper()
        print(f"Submitting answer for session {session_id}, mcq {mcq_id}. Chosen Letter: '{chosen_answer_letter}'")
        try:
            # Get MCQ
            mcq_stmt = select(GeneratedMCQ).where(GeneratedMCQ.mcq_id == mcq_id)
            mcq_result = await self.session.exec(mcq_stmt); mcq = mcq_result.first()
            if not mcq: raise ValueError(f"Question with ID {mcq_id} not found.")

            # Check Correctness

            # ----  Check Correctness  ------------------------------------------
            chosen_answer_letter = request_data.chosen_answer_letter.upper()

            correct_letter = mcq.correct_answer_letter.upper()      # ← field on DB
            options_map = {
                "A": mcq.option_a,
                "B": mcq.option_b,
                "C": mcq.option_c,
                "D": mcq.option_d,
            }
            correct_answer_text = options_map.get(correct_letter)
            if correct_answer_text is None:
                raise RuntimeError(
                    f"Internal error: invalid correct answer data for MCQ {mcq_id}."
                )

            is_correct = (chosen_answer_letter == correct_letter)
            print(
                f"Correctness check – chosen '{chosen_answer_letter}', "
                f"correct '{correct_letter}', result={is_correct}"
            )
# -------------------------------------------------------------------


# Check completion
            paper_id = mcq.paper_id
            all_paper_mcqs_stmt = select(GeneratedMCQ.mcq_id).where(GeneratedMCQ.paper_id == paper_id)
            all_paper_mcqs_res = await self.session.exec(all_paper_mcqs_stmt); total_mcqs_available = len(all_paper_mcqs_res.all())
            mastered_stmt = select(func.count(func.distinct(MCQAttempt.mcq_id))).join(GeneratedMCQ).where(MCQAttempt.session_uuid == session_id, GeneratedMCQ.paper_id == paper_id, MCQAttempt.is_correct == True) # Use correct field name
            mastered_count_res = await self.session.exec(mastered_stmt); mastered_count = mastered_count_res.one_or_none() or 0
            quiz_complete = (mastered_count >= total_mcqs_available) if total_mcqs_available > 0 else False
            print(f"Quiz completion check: Mastered={mastered_count}, Total={total_mcqs_available}, Complete={quiz_complete}")

            # Return feedback
            return GeneratedMCQAnswerFeedback(
                is_correct=is_correct,
                correct_answer_letter=correct_letter, # Use correct field name
                explanation=mcq.explanation or "No explanation available.",
                quiz_complete=quiz_complete
            )

        except Exception as e: await self.session.rollback(); print(f"ERROR during submit_answer: {e}"); traceback.print_exc(); raise RuntimeError(f"Internal server error processing answer: {e}") from e