"""Document category assignment."""

from app.core.config import get_settings
from app.services.document_classifier import classify_document_text


def test_missing_key_falls_back_to_general():
    settings = get_settings().model_copy(update={"gemini_api_key": ""})
    assert classify_document_text("leave policy for employees", settings) == "General"


def test_invalid_model_response_falls_back_to_general():
    settings = get_settings().model_copy(update={"gemini_api_key": "test-key"})

    def generate(_key, _model, _prompt):
        return {"category": "Unknown"}

    assert classify_document_text("salary bands", settings, generate=generate) == "General"


def test_valid_category_is_normalized():
    settings = get_settings().model_copy(update={"gemini_api_key": "test-key"})

    def generate(_key, _model, _prompt):
        return {"category": "hr"}

    assert classify_document_text("PTO accrual", settings, generate=generate) == "HR"
