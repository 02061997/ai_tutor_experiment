# backend/prompts/quiz_prompts.py

# Prompt to generate ONLY the question text
GENERATE_QUESTION_PROMPT_TEMPLATE = """
Based ONLY on the following text excerpt from a research paper, generate ONE clear, concise multiple-choice question that tests understanding of a key concept, method, finding, or definition presented *in the excerpt*.

Guidelines:
- The question should be answerable *directly* from the provided text.
- Focus on a single, important point.
- Avoid ambiguity.
- Output ONLY the question text itself. Do NOT include labels like "Question:", numbers, or any conversational text.

Excerpt:
---
{context_excerpt}
---

Question Text Only:"""

# Prompt to generate ONLY the correct answer AND 3 distractors
GENERATE_ANSWERS_PROMPT_TEMPLATE = """
Context Excerpt:
---
{context_excerpt}
---

Question:
{question_text}

Instructions:
1. Based ONLY on the Context Excerpt provided above, identify the single best CORRECT answer to the Question.
2. Generate exactly THREE plausible but INCORRECT options (distractors) based on information *related to* the excerpt's topic, but not directly supported as the answer by the excerpt itself. Distractors should be distinct from the correct answer and each other.
3. Format the output EXACTLY as follows, with each item on a NEW line:
   Correct Answer: [Insert the correct answer text here]
   Distractor 1: [Insert incorrect option 1 text here]
   Distractor 2: [Insert incorrect option 2 text here]
   Distractor 3: [Insert incorrect option 3 text here]

Output ONLY the lines starting with "Correct Answer:", "Distractor 1:", "Distractor 2:", and "Distractor 3:". Do NOT add any other text, explanations, or introductory/closing phrases.
"""

# Prompt to generate ONLY the explanation
GENERATE_EXPLANATION_PROMPT_TEMPLATE = """
Context Excerpt:
---
{context_excerpt}
---

Question:
{question_text}

Correct Answer:
{correct_answer_text}

Instructions:
Based ONLY on the Context Excerpt, write a brief, concise explanation (1-2 sentences) stating *why* the provided Correct Answer is correct according to the information in the excerpt. Focus solely on justification from the text.

Output ONLY the explanation text itself. Do NOT include labels like "Explanation:", introductions, or conversational filler.

Explanation Text Only:"""