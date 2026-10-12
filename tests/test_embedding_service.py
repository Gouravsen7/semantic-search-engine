"""Embedding service behavior without downloading a model."""

import pytest

from app.services.embedding_service import EmbeddingService


class _Vector:
    def __init__(self, values: list[float]) -> None:
        self._values = values

    def tolist(self) -> list[float]:
        return list(self._values)


class _Model:
    def __init__(self, width: int) -> None:
        self.width = width
        self.calls: list[list[str]] = []

    def encode(self, texts, normalize_embeddings=True, show_progress_bar=False):
        assert normalize_embeddings is True
        assert show_progress_bar is False
        self.calls.append(list(texts))
        return [_Vector([float(index)] * self.width) for index, _text in enumerate(texts)]


def test_embed_texts_returns_configured_dimension():
    service = EmbeddingService("test-model", 384)
    service._model = _Model(384)

    vectors = service.embed_texts(["one", "two"])

    assert len(vectors) == 2
    assert len(vectors[0]) == 384
    assert vectors[1][0] == 1.0
    assert service.embed_query("one")[0] == 0.0


def test_embed_texts_rejects_the_wrong_dimension():
    service = EmbeddingService("test-model", 384)
    service._model = _Model(3)

    with pytest.raises(RuntimeError, match="384"):
        service.embed_texts(["hello"])


def test_embed_texts_empty_input_skips_the_model():
    service = EmbeddingService("test-model", 384)
    assert service.embed_texts([]) == []
    assert service._model is None
