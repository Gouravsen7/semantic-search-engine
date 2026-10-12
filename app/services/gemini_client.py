"""HTTP client for Google Gemini generateContent."""

import json
import urllib.error
import urllib.request


class GeminiError(Exception):
    """Gemini rejected the request or returned nothing usable."""


def generate_text(api_key: str, model: str, prompt: str, *, temperature: float = 0.2, max_tokens: int = 512) -> str:
    payload = _post(
        api_key,
        model,
        prompt,
        temperature=temperature,
        max_tokens=max_tokens,
        response_mime_type=None,
    )
    try:
        text = payload["candidates"][0]["content"]["parts"][0]["text"]
    except (KeyError, IndexError, TypeError) as exc:
        raise GeminiError("Gemini returned an empty answer.") from exc
    cleaned = str(text).strip()
    if not cleaned:
        raise GeminiError("Gemini returned an empty answer.")
    return cleaned


def generate_json(
    api_key: str,
    model: str,
    prompt: str,
    *,
    temperature: float = 0.1,
    max_tokens: int = 256,
) -> dict:
    payload = _post(
        api_key,
        model,
        prompt,
        temperature=temperature,
        max_tokens=max_tokens,
        response_mime_type="application/json",
    )
    try:
        text = payload["candidates"][0]["content"]["parts"][0]["text"]
    except (KeyError, IndexError, TypeError) as exc:
        raise GeminiError("Gemini returned an empty answer.") from exc
    try:
        parsed = json.loads(str(text))
    except json.JSONDecodeError as exc:
        raise GeminiError("Gemini returned invalid JSON.") from exc
    if not isinstance(parsed, dict):
        raise GeminiError("Gemini returned invalid JSON.")
    return parsed


def _post(
    api_key: str,
    model: str,
    prompt: str,
    *,
    temperature: float,
    max_tokens: int,
    response_mime_type: str | None,
) -> dict:
    url = (
        "https://generativelanguage.googleapis.com/v1beta/models/"
        f"{model}:generateContent?key={api_key}"
    )
    generation_config: dict = {"temperature": temperature, "maxOutputTokens": max_tokens}
    if response_mime_type is not None:
        generation_config["responseMimeType"] = response_mime_type
    body = json.dumps(
        {
            "contents": [{"role": "user", "parts": [{"text": prompt}]}],
            "generationConfig": generation_config,
        }
    ).encode()
    request = urllib.request.Request(
        url,
        data=body,
        headers={"Content-Type": "application/json"},
        method="POST",
    )
    try:
        with urllib.request.urlopen(request, timeout=30) as response:
            return json.loads(response.read().decode())
    except urllib.error.HTTPError as exc:
        detail = exc.read().decode(errors="replace")[:300]
        raise GeminiError(detail or exc.reason) from exc
    except (urllib.error.URLError, TimeoutError) as exc:
        raise GeminiError("Gemini is unavailable.") from exc
