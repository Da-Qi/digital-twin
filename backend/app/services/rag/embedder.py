"""Local embedding service using sentence-transformers."""

import numpy as np
from numpy.typing import NDArray
from sentence_transformers import SentenceTransformer

from app.config import settings


class EmbedderService:
    """Generates embeddings using a local model (BGE-large by default)."""

    def __init__(self, model_name: str | None = None):
        self.model_name = model_name or settings.embedding_model
        self._model: SentenceTransformer | None = None

    @property
    def model(self) -> SentenceTransformer:
        if self._model is None:
            self._model = SentenceTransformer(self.model_name)
            self._model.half()  # FP16 for memory efficiency
        return self._model

    @property
    def dimension(self) -> int:
        return self.model.get_sentence_embedding_dimension()

    def encode(self, texts: list[str], batch_size: int = 32) -> NDArray[np.float32]:
        """Encode a list of texts into embeddings."""
        return self.model.encode(texts, batch_size=batch_size, normalize_embeddings=True, show_progress_bar=False)

    def encode_query(self, text: str) -> NDArray[np.float32]:
        """Encode a single query (no prefix needed for BGE)."""
        return self.encode([text])[0]


embedder = EmbedderService()
