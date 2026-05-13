"""End-to-end pipeline test using the mock embedder + FAISS store + mock LLM."""
import pytest

from app.Services.embedding_service import VertexLikeEmbedder
from app.Services.faiss_vector_store import FaissVectorStore
from app.Services.rag_pipeline import RAGPipeline
from app.Services.query_expander import QueryExpander
from app.Services.llm_provider import MockProvider


@pytest.fixture
def pipeline(tmp_path):
    store = FaissVectorStore(path=str(tmp_path / "store"), dim=384)
    mock_llm = MockProvider()
    return RAGPipeline(
        embedder=VertexLikeEmbedder(),
        vector_store=store,
        query_expander=QueryExpander(mock_llm),
        generator=mock_llm,
    )


def test_ingest_creates_chunks(pipeline):
    res = pipeline.ingest_text(
        "Auto-scaling handles peak load via Kubernetes HPA. "
        "When CPU exceeds 70 percent, new pods are spawned.",
        source="autoscale.txt")
    assert res.chunk_count >= 1
    assert pipeline.store.count() >= 1


def test_strategy_a_returns_results(pipeline):
    pipeline.ingest_text("Failover happens when the primary database fails.",
                         source="db.txt")
    results, expanded, _ = pipeline.retrieve("database outage", strategy="A",
                                              top_k=1)
    assert expanded == ""
    assert len(results) >= 1
    assert all(r.strategy == "A" for r in results)


def test_strategy_b_expands_query(pipeline):
    pipeline.ingest_text("Failover happens when primary database fails.",
                         source="db.txt")
    results, expanded, _ = pipeline.retrieve("outage", strategy="B", top_k=1)
    assert expanded != ""
    assert all(r.strategy == "B" for r in results)


def test_ask_returns_full_query_result(pipeline):
    pipeline.ingest_text("Caching uses Redis and CDN to reduce database load.",
                         source="cache.txt")
    qr = pipeline.ask("How is caching done?", strategy="B", top_k=2)
    assert qr.answer
    assert qr.strategy == "B"
    assert qr.latency_ms > 0


def test_delete_removes_vectors(pipeline):
    res = pipeline.ingest_text("Content to be deleted.", source="del.txt")
    before = pipeline.store.count()
    removed = pipeline.delete_document(res.doc_id)
    assert removed >= 1
    assert pipeline.store.count() == before - removed
