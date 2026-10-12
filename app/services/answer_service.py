"""Write a plain-language answer from the passages found by search."""

import re

from app.core.config import Settings
from app.services.gemini_client import GeminiError, generate_text

NOT_FOUND = "Not found in your documents."
MISSING_KEY = "Set GEMINI_API_KEY in the .env file to generate an answer."


class AnswerService:
    def __init__(self, settings: Settings, generate=generate_text) -> None:
        self.settings = settings
        self._generate = generate

    def answer(
        self,
        query: str,
        passages: list[tuple[str, str]],
        *,
        category: str | None = None,
        interpreted_query: str | None = None,
    ) -> str:
        if not passages:
            return NOT_FOUND
        if not self.settings.gemini_api_key:
            return MISSING_KEY
        try:
            return _clean_answer(
                self._generate(
                    self.settings.gemini_api_key,
                    self.settings.gemini_model,
                    _prompt(query, passages, category=category, interpreted_query=interpreted_query),
                )
            )
        except GeminiError as exc:
            return f"Answer could not be generated: {exc}"


_PREAMBLE = re.compile(
    r"^based on the provided (?:passages|passage|documents|document)\s*[,:]?\s*",
    re.IGNORECASE,
)


def _clean_answer(text: str) -> str:
    cleaned = _PREAMBLE.sub("", text.strip(), count=1).strip()
    if cleaned[:1].islower():
        cleaned = cleaned[0].upper() + cleaned[1:]
    return cleaned or text.strip()


def _prompt(
    query: str,
    passages: list[tuple[str, str]],
    *,
    category: str | None,
    interpreted_query: str | None,
) -> str:
    lines = []
    for index, (filename, content) in enumerate(passages, start=1):
        lines.append(f"[{index}] {filename}: {content}")
    excerpts = "\n".join(lines)
    context_lines = []
    if category:
        context_lines.append(f"Document category in scope: {category}.")
    if interpreted_query and interpreted_query.strip() != query.strip():
        context_lines.append(f"Interpreted question: {interpreted_query.strip()}.")
    context = "\n".join(context_lines)
    context_block = f"{context}\n\n" if context else ""
    return (
        "Answer the question using only the passages below. "
        "Use plain language, in the same language as the question. "
        "If a passage discusses the question, explain the detail it states, including a maximum, a limit, or a related rule. "
        "Say that it was not found in the documents only when the passages do not discuss the question. "
        "Start with the answer. Do not mention the passages or begin with 'Based on the provided passages'. "
        "Do not use outside knowledge.\n\n"
        f"{context_block}"
        f"Question:\n{query}\n\n"
        f"Passages:\n{excerpts}"
    )
