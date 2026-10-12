"""Interpret a search query into category and retrieval text."""

from dataclasses import dataclass

from app.core.config import Settings
from app.services.document_categories import normalize_category
from app.services.gemini_client import GeminiError, generate_json

_LABELS = "HR, Legal, Finance, Technical, Policy, General"


@dataclass(frozen=True)
class UnderstoodQuery:
    category: str
    search_text: str
    routed: bool


def understand_query(query: str, settings: Settings, generate=generate_json) -> UnderstoodQuery:
    cleaned = query.strip()
    if not cleaned:
        return UnderstoodQuery(category="General", search_text=cleaned, routed=False)
    if not settings.gemini_api_key:
        return UnderstoodQuery(category="General", search_text=cleaned, routed=False)
    prompt = (
        "Analyze the user's question for document search. "
        f"Pick the best document category from: {_LABELS}. "
        "Rewrite the question into a short search phrase for semantic retrieval. "
        'Reply with JSON only: {"category": "<category>", "search_text": "<rewritten query>"}.\n\n'
        f"Question:\n{cleaned}"
    )
    try:
        payload = generate(settings.gemini_api_key, settings.gemini_model, prompt)
    except GeminiError:
        return UnderstoodQuery(category="General", search_text=cleaned, routed=False)
    category = normalize_category(str(payload.get("category", "")))
    search_text = str(payload.get("search_text", "")).strip() or cleaned
    return UnderstoodQuery(category=category, search_text=search_text, routed=True)
