"""Load the sentence-transformer model and encode text."""

import logging
import threading

logger = logging.getLogger(__name__)


class EmbeddingService:
    """Encodes text with a single shared model.

    The model is loaded on first use so tests and startup do not download it.
    Encoding is serialized because the model is shared by request threads.
    """

    def __init__(self, model_name: str, dimension: int) -> None:
        self.model_name = model_name
        self.dimension = dimension
        self._model = None
        self._lock = threading.Lock()

    def embed_texts(self, texts: list[str]) -> list[list[float]]:
        if not texts:
            return []

        model = self._get_model()
        with self._lock:
            encoded = model.encode(
                texts,
                normalize_embeddings=True,
                show_progress_bar=False,
            )

        vectors: list[list[float]] = []
        for vector in encoded:
            values = vector.tolist() if hasattr(vector, "tolist") else list(vector)
            floats = [float(value) for value in values]
            if len(floats) != self.dimension:
                raise RuntimeError(
                    f"Expected {self.dimension}-dimensional embeddings, got {len(floats)}."
                )
            vectors.append(floats)
        return vectors

    def embed_query(self, query: str) -> list[float]:
        return self.embed_texts([query])[0]

    def _get_model(self):
        if self._model is not None:
            return self._model

        with self._lock:
            if self._model is None:
                from sentence_transformers import SentenceTransformer

                logger.info("Loading embedding model %s", self.model_name)
                self._model = SentenceTransformer(self.model_name)
        return self._model
