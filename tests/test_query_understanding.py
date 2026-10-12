"""Search query interpretation."""

from app.core.config import get_settings
from app.services.query_understanding import understand_query


def test_missing_key_keeps_original_query():
    settings = get_settings().model_copy(update={"gemini_api_key": ""})
    result = understand_query("  annual leave limit  ", settings)
    assert result.routed is False
    assert result.search_text == "annual leave limit"
    assert result.category == "General"


def test_gemini_response_is_used():
    settings = get_settings().model_copy(update={"gemini_api_key": "test-key"})

    def generate(_key, _model, _prompt):
        return {"category": "Policy", "search_text": "maximum annual leave days"}

    result = understand_query("how many leave days?", settings, generate=generate)
    assert result.routed is True
    assert result.category == "Policy"
    assert result.search_text == "maximum annual leave days"
