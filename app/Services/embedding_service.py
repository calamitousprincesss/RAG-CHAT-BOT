"""Local embedding via sentence-transformers (simulates Vertex textembedding-gecko).

`SentenceTransformerEmbedder` is the production implementation.
`VertexLikeEmbedder` wraps the mocked Vertex SDK for testing the swap path.
"""
from __future__ import annotations
import numpy as np
from app.Services.interfaces import IEmbedder
from app.Config.settings import settings


class SentenceTransformerEmbedder(IEmbedder):
    """L2-normalized embeddings so cosine similarity reduces to dot product."""

    def __init__(self, model_name: str | None = None):
        from sentence_transformers import SentenceTransformer
        self._model = SentenceTransformer(model_name or settings.embedding_model)
        self._dim = int(self._model.get_sentence_embedding_dimension())

    @property
    def dim(self) -> int:
        return self._dim

    def embed(self, texts: list[str]) -> list[list[float]]:
        if not texts:
            return []
        arr = self._model.encode(texts, normalize_embeddings=True,
                                 convert_to_numpy=True, show_progress_bar=False)
        return arr.astype(np.float32).tolist()

    def embed_one(self, text: str) -> list[float]:
        return self.embed([text])[0]


class VertexLikeEmbedder(IEmbedder):
    """Wraps the mocked Vertex SDK so the same interface drives both impls."""

    def __init__(self, model_name: str = "textembedding-gecko@003"):
        from app.Mocks.mock_vertex import MockTextEmbeddingModel
        self._model = MockTextEmbeddingModel.from_pretrained(model_name)

    @property
    def dim(self) -> int:
        return self._model.dim

    def embed(self, texts: list[str]) -> list[list[float]]:
        return [e.values for e in self._model.get_embeddings(texts)]

    def embed_one(self, text: str) -> list[float]:
        return self.embed([text])[0]
