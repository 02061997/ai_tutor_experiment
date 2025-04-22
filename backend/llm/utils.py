# backend/llm/utils.py
from __future__ import annotations

import re
import logging
from typing import Tuple, List

logger = logging.getLogger(__name__)

def parse_llm_answers_and_distractors(llm_output: str) -> Tuple[str | None, List[str]]:
    """
    Parses the expected structured output from the LLM for the correct answer
    and exactly three distractors.

    Expects input format like:
    Correct Answer: [Answer text]
    Distractor 1: [Distractor 1 text]
    Distractor 2: [Distractor 2 text]
    Distractor 3: [Distractor 3 text]

    Args:
        llm_output: The raw text output string from the LLM.

    Returns:
        A tuple containing:
        - The extracted correct answer text (str or None if not found/parsed).
        - A list of exactly three extracted distractor texts (list[str]).
          Returns an empty list if parsing fails to find three distractors.
    """
    correct_answer = None
    distractors = {} # Use a dict to store distractors by number initially

    # Remove potential markdown list characters and trim lines
    lines = [line.strip().lstrip('*- ') for line in llm_output.strip().split('\n') if line.strip()]
    logger.debug(f"Parsing LLM answer output lines: {lines}")

    # Regex patterns to capture the text after the label, case-insensitive
    ca_pattern = re.compile(r"Correct Answer:\s*(.*)", re.IGNORECASE)
    d1_pattern = re.compile(r"Distractor\s+1:\s*(.*)", re.IGNORECASE)
    d2_pattern = re.compile(r"Distractor\s+2:\s*(.*)", re.IGNORECASE)
    d3_pattern = re.compile(r"Distractor\s+3:\s*(.*)", re.IGNORECASE)

    for line in lines:
        ca_match = ca_pattern.match(line)
        d1_match = d1_pattern.match(line)
        d2_match = d2_pattern.match(line)
        d3_match = d3_pattern.match(line)

        if ca_match:
            correct_answer = ca_match.group(1).strip()
            logger.debug(f"Parsed Correct Answer: '{correct_answer}'")
        elif d1_match:
            distractors[1] = d1_match.group(1).strip()
            logger.debug(f"Parsed Distractor 1: '{distractors[1]}'")
        elif d2_match:
            distractors[2] = d2_match.group(1).strip()
            logger.debug(f"Parsed Distractor 2: '{distractors[2]}'")
        elif d3_match:
            distractors[3] = d3_match.group(1).strip()
            logger.debug(f"Parsed Distractor 3: '{distractors[3]}'")

    # Validate results
    if not correct_answer:
        logger.warning(f"Could not parse 'Correct Answer:' from LLM output:\n{llm_output}")
        return None, [] # Indicate failure

    # Ensure we have exactly 3 distractors in the correct order
    final_distractors = [distractors.get(i) for i in range(1, 4)]
    if None in final_distractors or not all(final_distractors): # Check for missing or empty distractors
        logger.warning(f"Parsed {len([d for d in final_distractors if d])} valid distractors (expected 3) from LLM output:\n{llm_output}")
        return None, [] # Indicate failure if not exactly 3 non-empty distractors

    logger.info(f"Successfully parsed Correct Answer and 3 Distractors.")
    return correct_answer, final_distractors # Return correct answer and list of 3 distractors