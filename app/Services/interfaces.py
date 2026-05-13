"""Abstract interfaces for the embedder, vector store, and LLM."""
from abc import ABC, abstractmethod
from typing import Any
from app.DTOs import Chunk, RetrievalResult


class IEmbedder(ABC):
    @abstractmethod
    def embed(self, texts: list[str]) -> list[list[float]]: ...

    @abstractmethod
    def embed_one(self, text: str) -> list[float]: ...

    @property
    @abstractmethod
    def dim(self) -> int: ...


class IVectorStore(ABC):
    @abstractmethod
    def add(self, chunks: list[Chunk], vectors: list[list[float]]) -> None: ...

    @abstractmethod
    def search(self, vector: list[float], top_k: int = 3,
               where: dict | None = None) -> list[RetrievalResult]: ...

    @abstractmethod
    def delete_by_doc(self, doc_id: str) -> int: ...

    @abstractmethod
    def count(self) -> int: ...

    @abstractmethod
    def all_texts(self) -> list[dict[str, Any]]: ...


class ILLM(ABC):
    @abstractmethod
    def generate(self, prompt: str, **kwargs) -> str: ...

    @abstractmethod
    def rewrite_query(self, query: str) -> str: ...
