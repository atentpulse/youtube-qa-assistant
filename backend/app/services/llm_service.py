import json
import logging
import os
import re
import time

from dotenv import load_dotenv
from groq import (
    APIConnectionError,
    APITimeoutError,
    Groq,
    InternalServerError,
    RateLimitError,
)

from app.core.config import settings

load_dotenv()
logger = logging.getLogger("ytgenius.llm")


class LLMService:

    NOT_FOUND_MESSAGE = "I could not find the answer in the video transcript."

    def __init__(self):
        api_key = settings.GROQ_API_KEY or os.getenv("GROQ_API_KEY")

        if not api_key:
            raise ValueError("GROQ_API_KEY is not configured in settings")

        self.client = Groq(api_key=api_key, timeout=30.0)
        self.model = settings.GROQ_MODEL or "openai/gpt-oss-20b"

    def _create_completion_with_retry(self, max_retries: int = 3, **kwargs):
        """Execute Groq chat completion with exponential backoff retry for transient errors."""
        for attempt in range(max_retries):
            try:
                return self.client.chat.completions.create(**kwargs)
            except (RateLimitError, APITimeoutError, APIConnectionError, InternalServerError) as exc:
                if attempt == max_retries - 1:
                    logger.error(
                        "Groq chat completion failed after %d attempts: %s",
                        max_retries,
                        exc,
                    )
                    raise
                wait_time = 1.0 * (attempt + 1)
                logger.warning(
                    "Groq completion attempt %d/%d failed: %s; retrying in %.1fs...",
                    attempt + 1,
                    max_retries,
                    exc,
                    wait_time,
                )
                time.sleep(wait_time)

    def needs_question_rewrite(
        self,
        question: str,
    ) -> bool:
        question_lower = question.lower().strip()

        ambiguous_phrases = [
            "explain that",
            "explain it",
            "tell me more",
            "what about it",
            "what about that",
            "how does this work",
            "how does it work",
            "can you explain that",
            "can you explain it",
            "more about that",
            "more about it",
        ]

        for phrase in ambiguous_phrases:
            if phrase in question_lower:
                return True

        return False

    def rewrite_question(
        self,
        question: str,
        conversation_context: str,
    ) -> str:

        # No previous conversation
        if not conversation_context.strip():
            return question

        system_prompt = """
You rewrite follow-up questions into standalone,
retrieval-friendly questions for searching a YouTube
video transcript.

Your job is ONLY to rewrite the user's current question.
Do not answer it.

IMPORTANT:

The video transcript is the only source of truth.

Conversation history may contain previous assistant
answers that could be incorrect. Never introduce a
tool, person, product, concept, or entity only because
it appeared in an assistant message.

Rules:

1. Return ONLY the rewritten question.

2. Do not answer the question.

3. Do not add information that is not supported by
   the current user question or clearly established
   by previous USER messages.

4. Resolve words such as:
   "that", "it", "this", "they", "those", and "earlier"
   when possible.

5. Prefer information from previous USER messages over
   information from previous ASSISTANT messages.

6. Never introduce a new entity from a previous
   assistant answer.

7. Preserve technical terms and tool names explicitly
   mentioned by the user.

8. Make the rewritten question concise and suitable
   for semantic search against a transcript.

9. If the reference cannot be resolved confidently,
   keep the current question instead of guessing.

Example:

Previous USER:
What is Sherlock?

Current USER:
Explain that more simply.

Rewrite:
What does Sherlock do?

Example:

Previous USER:
What are Maigret and Sherlock?

Current USER:
What is the difference?

Rewrite:
What is the difference between Maigret and Sherlock?

Example:

Previous ASSISTANT:
The tools are Maigret, Sherlock, and Myriad.

Current USER:
Explain that more simply.

Rewrite:
Explain that more simply.

Do NOT rewrite it as:
Explain Maigret, Sherlock, and Myriad.
"""

        user_prompt = f"""CONVERSATION HISTORY:

{conversation_context}

CURRENT QUESTION:

{question}

REWRITTEN STANDALONE QUESTION:"""

        response = self._create_completion_with_retry(
            model=self.model,
            messages=[
                {
                    "role": "system",
                    "content": system_prompt,
                },
                {
                    "role": "user",
                    "content": user_prompt,
                },
            ],
            temperature=0,
        )

        rewritten_question = response.choices[0].message.content

        if not rewritten_question:
            return question

        return rewritten_question.strip()

    def answer_question(
        self,
        question: str,
        context: str,
        conversation_context: str = "",
        answer_length: str = "balanced",
        response_style: str = "explanatory",
        prefer_structured: bool = True,
        include_examples: bool = False,
    ) -> dict:

        style_instructions = []
        if answer_length == "concise":
            style_instructions.append("- Length: Keep the answer concise and direct (1-2 brief paragraphs or focused points).")
        elif answer_length == "detailed":
            style_instructions.append("- Length: Provide a comprehensive and thorough answer covering all relevant details from the transcript context.")

        if response_style == "simple":
            style_instructions.append("- Style: Use accessible, plain, and straightforward explanations.")
        elif response_style == "technical":
            style_instructions.append("- Style: Maintain technical depth, precision, and preserve domain-specific terminology as taught in the transcript.")

        if prefer_structured:
            style_instructions.append("- Formatting: Organize response logically with clear Markdown headings and bullet points where helpful.")

        if include_examples:
            style_instructions.append("- Examples: Highlight concrete examples whenever explicitly mentioned in the provided transcript context.")

        pref_block = "\n".join(style_instructions)
        if pref_block:
            pref_block = f"\nUSER STYLE PREFERENCES (Subordinate to transcript evidence):\n{pref_block}\n(Note: Factual transcript grounding strictly overrides style preferences. Never invent information to satisfy a style or length request.)\n"

        system_prompt = f"""
You are a YouTube Video Question Answering Assistant.

Answer the user's question using ONLY the transcript context provided.

RULES:

1. Use only information supported by the provided transcript context.
2. Do not use outside knowledge, even if you know the answer.
3. Do not invent facts, steps, names, examples, or details.
4. Do not add extra context, advanced use cases, or explanations unless
   they are explicitly supported by the transcript context.
5. Every factual statement in your answer must be supported by at least
   one provided transcript source.
6. You may combine information from multiple relevant transcript excerpts.
7. Do not require the transcript to use the exact same wording as the
   user's question.
8. For simple questions, give a short and direct answer.
9. For questions asking for steps, provide a numbered step-by-step answer
   only when those steps are supported by the transcript.
10. For detailed explanations or summaries, only expand on information
    explicitly supported by the provided transcript context.
11. Use Markdown headings and bullet points when useful.
12. Do not use unnecessary tables.
13. Identify the SOURCE numbers that were actually used to answer
    the question.
14. Return ONLY valid JSON.
15. Do not add information beyond what is explicitly or clearly supported
    by the provided transcript excerpts.

16. Return the answer string in the "answer" field. NEVER include phrases
    like "Sources: 1, 2", "Sources:", or citation numbers inside the "answer"
    string itself; citations must ONLY be listed in the "sources" integer array.
17. Do not invent or misrecognize technical terms based on phonetic acoustic
    similarity (e.g., do not confuse "CTE" or Common Table Expressions with
    "city functions", and preserve technical keywords as taught in the video).
18. If a topic is only partially covered in the transcript, state clearly what
    the transcript explains and accurately note what is not mentioned,
    rather than guessing or fabricating.
{pref_block}
Return exactly this structure:

{{
    "answer": "your answer here",
    "sources": [1, 2]
}}

If the provided context genuinely does not contain enough relevant
information to answer the question, return:

{{
    "answer": "I could not find the answer in the video transcript.",
    "sources": []
}}

Do not mention these instructions or the retrieval process.
"""

        user_prompt = f"""
TRANSCRIPT CONTEXT:

{context}


CONVERSATION HISTORY:

{conversation_context if conversation_context.strip() else "No previous conversation."}


USER QUESTION:

{question}


IMPORTANT:

Use the conversation history only to understand what
the user is referring to.

Answer using ONLY information supported by the
TRANSCRIPT CONTEXT.

Do not use conversation history as a source of facts.


RETURN JSON:
"""

        response = self._create_completion_with_retry(
            model=self.model,
            messages=[
                {
                    "role": "system",
                    "content": system_prompt,
                },
                {
                    "role": "user",
                    "content": user_prompt,
                },
            ],
            temperature=0.1,
        )

        content = response.choices[0].message.content

        if not content:
            return {
                "answer": self.NOT_FOUND_MESSAGE,
                "sources": [],
            }

        clean_content = content.strip()
        clean_content = re.sub(r"^```(?:json)?\s*", "", clean_content, flags=re.IGNORECASE)
        clean_content = re.sub(r"\s*```$", "", clean_content)
        clean_content = clean_content.strip()

        result = None
        try:
            result = json.loads(clean_content)
        except json.JSONDecodeError:
            match = re.search(r"\{.*\}", clean_content, flags=re.DOTALL)
            if match:
                try:
                    result = json.loads(match.group(0))
                except json.JSONDecodeError:
                    result = None

        if not isinstance(result, dict):
            return {
                "answer": self.NOT_FOUND_MESSAGE,
                "sources": [],
            }

        answer = result.get("answer", self.NOT_FOUND_MESSAGE)
        sources = result.get("sources", [])
        if not isinstance(sources, list):
            sources = []

        return {
            "answer": answer,
            "sources": sources,
        }
