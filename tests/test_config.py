"""Settings validation."""

import pytest
from pydantic import ValidationError

from app.core.config import Settings


def test_overlap_must_be_smaller_than_chunk_size():
    with pytest.raises(ValidationError, match="CHUNK_OVERLAP"):
        Settings(chunk_size=10, chunk_overlap=10)


def test_default_top_k_cannot_exceed_the_maximum():
    with pytest.raises(ValidationError, match="DEFAULT_TOP_K"):
        Settings(default_top_k=10, max_top_k=5)


def test_insecure_jwt_secret_is_rejected_without_opt_in():
    with pytest.raises(ValidationError, match="JWT_SECRET"):
        Settings(jwt_secret="local-dev-secret-change-before-exposing", allow_insecure_jwt=False)


def test_insecure_jwt_allowed_when_explicitly_enabled():
    settings = Settings(jwt_secret="local-dev-secret-change-before-exposing", allow_insecure_jwt=True)
    assert settings.allow_insecure_jwt is True
