"""Assign a fixed document category from extracted text."""

from app.core.config import Settings
from app.services.document_categories import DOCUMENT_CATEGORIES, GENERAL, normalize_category
from app.services.gemini_client import GeminiError, generate_json

_EXCERPT_LIMIT = 6000


def classify_document_text(text: str, settings: Settings, generate=generate_json) -> str:
    excerpt = text.strip()[:_EXCERPT_LIMIT]
    if not excerpt or not settings.gemini_api_key:
        return GENERAL
    labels = ", ".join(DOCUMENT_CATEGORIES)
    prompt = (
        "Choose exactly one document category for the excerpt below. "
        f"Categories: {labels}. "
        'Reply with JSON only: {"category": "<one of the categories>"}.\n\n'
        f"Excerpt:\n{excerpt}"
    )
    try:
        payload = generate(settings.gemini_api_key, settings.gemini_model, prompt)
    except GeminiError:
        return GENERAL
    return normalize_category(str(payload.get("category", "")))
