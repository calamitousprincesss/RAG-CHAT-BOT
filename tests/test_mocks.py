"""Verifies our mocks match the Vertex AI SDK shape (PDF mocking requirement)."""
from app.Mocks.mock_vertex import (
    MockTextEmbeddingModel, MockGenerativeModel, TextEmbedding, GenerationResponse
)


def test_text_embedding_model_from_pretrained_returns_instance():
    m = MockTextEmbeddingModel.from_pretrained("textembedding-gecko@003")
    assert isinstance(m, MockTextEmbeddingModel)


def test_text_embedding_model_get_embeddings_shape():
    m = MockTextEmbeddingModel(dim=384)
    out = m.get_embeddings(["hello world", "another sentence"])
    assert len(out) == 2
    assert isinstance(out[0], TextEmbedding)
    assert len(out[0].values) == 384


def test_text_embedding_deterministic():
    m = MockTextEmbeddingModel(dim=64)
    a = m.get_embeddings(["same text"])[0].values
    b = m.get_embeddings(["same text"])[0].values
    assert a == b


def test_generative_model_returns_generation_response():
    g = MockGenerativeModel("gemini-1.5-flash")
    resp = g.generate_content("Rewrite this query: peak load")
    assert isinstance(resp, GenerationResponse)
    assert isinstance(resp.text, str)
    assert resp.usage_metadata["prompt_token_count"] > 0


def test_generative_model_rewrite_adds_synonyms():
    g = MockGenerativeModel()
    r = g.generate_content("Rewrite this query: peak load")
    assert "scalability" in r.text or "load" in r.text.lower()
