from app.Services.llm_provider import LLMFactory, MockProvider


def test_factory_default_returns_mock():
    inst = LLMFactory.create("mock")
    assert isinstance(inst, MockProvider)


def test_factory_available_has_mock():
    avail = LLMFactory.available()
    assert avail["mock"] is True


def test_mock_provider_generate():
    p = MockProvider()
    out = p.generate("Context: x\nQuestion: y\nAnswer:")
    assert isinstance(out, str)
    assert len(out) > 0


def test_mock_provider_rewrite_returns_string():
    p = MockProvider()
    out = p.rewrite_query("peak load")
    assert isinstance(out, str)
    assert "load" in out.lower() or len(out) > 0
