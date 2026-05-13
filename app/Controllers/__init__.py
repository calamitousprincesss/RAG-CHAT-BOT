from app.Services.embedding_service import SentenceTransformerEmbedder
from app.Services.faiss_vector_store import FaissVectorStore
from app.Services.rag_pipeline import RAGPipeline

_pipeline: RAGPipeline | None = None


def _make_vector_store():
    return FaissVectorStore()


def get_pipeline() -> RAGPipeline:
    global _pipeline
    if _pipeline is None:
        _pipeline = RAGPipeline(
            embedder=SentenceTransformerEmbedder(),
            vector_store=_make_vector_store(),
        )
    return _pipeline
