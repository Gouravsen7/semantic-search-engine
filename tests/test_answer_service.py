"""Answers are written only from retrieved passages."""

from app.core.config import get_settings
from app.services.answer_service import MISSING_KEY, NOT_FOUND, AnswerService


def test_no_passages_skips_gemini():
    calls = []
    service = AnswerService(get_settings(), generate=lambda *_args: calls.append(True))

    assert service.answer("how many leaves", []) == NOT_FOUND
    assert calls == []


def test_missing_key_does_not_call_gemini():
    calls = []
    settings = get_settings().model_copy(update={"gemini_api_key": ""})
    service = AnswerService(settings, generate=lambda *_args: calls.append(True))

    text = service.answer("how many leaves", [("policy.pdf", "18 leaves a year")])

    assert text == MISSING_KEY
    assert calls == []


def test_answer_comes_from_the_passages():
    settings = get_settings().model_copy(update={"gemini_api_key": "test-key", "gemini_model": "gemini-3.8-flash"})

    def post(api_key, model, prompt):
        assert api_key == "test-key"
        assert model == "gemini-3.8-flash"
        assert "how many leaves" in prompt
        assert "18 leaves a year" in prompt
        return "You can take 18 leaves in a year."

    service = AnswerService(settings, generate=post)
    assert service.answer("how many leaves", [("policy.pdf", "18 leaves a year")]) == (
        "You can take 18 leaves in a year."
    )


def test_answer_includes_category_and_interpretation_in_prompt():
    settings = get_settings().model_copy(update={"gemini_api_key": "test-key"})
    captured = []

    def generate(api_key, model, prompt):
        captured.append(prompt)
        return "18 days."

    service = AnswerService(settings, generate=generate)
    service.answer(
        "leave limit",
        [("policy.pdf", "18 days per year")],
        category="HR",
        interpreted_query="maximum annual leave",
    )
    assert "Document category in scope: HR." in captured[0]
    assert "Interpreted question: maximum annual leave." in captured[0]


def test_answer_drops_the_passages_preamble():
    settings = get_settings().model_copy(update={"gemini_api_key": "test-key"})
    service = AnswerService(
        settings,
        generate=lambda *_args: "Based on the provided passages, paternity leave is a maximum of 7 working days.",
    )

    assert service.answer("paternity leave", [("policy.pdf", "maximum of 7 working days")]) == (
        "Paternity leave is a maximum of 7 working days."
    )
