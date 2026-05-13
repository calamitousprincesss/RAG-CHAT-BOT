"""Pluggable LLM providers behind ILLM. Selected via LLM_PROVIDER env var."""
from __future__ import annotations
import requests
from app.Services.interfaces import ILLM
from app.Mocks.mock_vertex import MockGenerativeModel
from app.Config.settings import settings


REWRITE_PROMPT = (
    "Rewrite and expand the following user query to be more "
    "embedding-friendly for semantic vector search. Add synonyms and "
    "related technical terms. Return ONLY the expanded query — no preamble.\n\n"
    "Query: {query}"
)


class MockProvider(ILLM):
    name = "mock"
    def __init__(self, model: str = "mock-vertex-gemini"):
        self.model = model
        self._impl = MockGenerativeModel(model)

    def generate(self, prompt: str, **kwargs) -> str:
        return self._impl.generate_content(prompt).text

    def rewrite_query(self, query: str) -> str:
        return self._impl.generate_content(
            REWRITE_PROMPT.format(query=query)
        ).text.strip()


class OpenAIProvider(ILLM):
    name = "openai"
    def __init__(self, api_key: str, model: str | None = None,
                 base_url: str | None = None):
        self.api_key = api_key
        self.model = model or "gpt-4o-mini"
        self.base_url = (base_url or "https://api.openai.com/v1").rstrip("/")

    def _chat(self, prompt: str, max_tokens: int = 512) -> str:
        r = requests.post(
            f"{self.base_url}/chat/completions",
            headers={"Authorization": f"Bearer {self.api_key}",
                     "Content-Type": "application/json"},
            json={"model": self.model,
                  "messages": [{"role": "user", "content": prompt}],
                  "max_tokens": max_tokens, "temperature": 0.2},
            timeout=60,
        )
        r.raise_for_status()
        return r.json()["choices"][0]["message"]["content"].strip()

    def generate(self, prompt: str, **kwargs) -> str:
        return self._chat(prompt, max_tokens=kwargs.get("max_tokens", 512))

    def rewrite_query(self, query: str) -> str:
        return self._chat(REWRITE_PROMPT.format(query=query), max_tokens=120)


class AnthropicProvider(ILLM):
    name = "anthropic"
    def __init__(self, api_key: str, model: str | None = None):
        self.api_key = api_key
        self.model = model or "claude-haiku-4-5-20251001"

    def _chat(self, prompt: str, max_tokens: int = 512) -> str:
        r = requests.post(
            "https://api.anthropic.com/v1/messages",
            headers={"x-api-key": self.api_key,
                     "anthropic-version": "2023-06-01",
                     "Content-Type": "application/json"},
            json={"model": self.model, "max_tokens": max_tokens,
                  "messages": [{"role": "user", "content": prompt}]},
            timeout=60,
        )
        r.raise_for_status()
        data = r.json()
        return "".join(b.get("text", "") for b in data.get("content", [])).strip()

    def generate(self, prompt: str, **kwargs) -> str:
        return self._chat(prompt, max_tokens=kwargs.get("max_tokens", 512))

    def rewrite_query(self, query: str) -> str:
        return self._chat(REWRITE_PROMPT.format(query=query), max_tokens=120)


class GeminiProvider(ILLM):
    name = "gemini"
    def __init__(self, api_key: str, model: str | None = None):
        self.api_key = api_key
        self.model = model or "gemini-1.5-flash"

    def _chat(self, prompt: str, max_tokens: int = 512) -> str:
        url = (f"https://generativelanguage.googleapis.com/v1beta/"
               f"models/{self.model}:generateContent?key={self.api_key}")
        r = requests.post(
            url, headers={"Content-Type": "application/json"},
            json={"contents": [{"parts": [{"text": prompt}]}],
                  "generationConfig": {"maxOutputTokens": max_tokens,
                                       "temperature": 0.2}},
            timeout=60,
        )
        r.raise_for_status()
        data = r.json()
        try:
            return data["candidates"][0]["content"]["parts"][0]["text"].strip()
        except (KeyError, IndexError):
            return ""

    def generate(self, prompt: str, **kwargs) -> str:
        return self._chat(prompt, max_tokens=kwargs.get("max_tokens", 512))

    def rewrite_query(self, query: str) -> str:
        return self._chat(REWRITE_PROMPT.format(query=query), max_tokens=120)


class OllamaProvider(ILLM):
    name = "ollama"
    def __init__(self, base_url: str, model: str | None = None):
        self.base_url = base_url.rstrip("/")
        self.model = model or "llama3.2:3b"

    def _chat(self, prompt: str) -> str:
        r = requests.post(
            f"{self.base_url}/api/generate",
            json={"model": self.model, "prompt": prompt, "stream": False},
            timeout=120,
        )
        r.raise_for_status()
        return r.json().get("response", "").strip()

    def generate(self, prompt: str, **kwargs) -> str:
        return self._chat(prompt)

    def rewrite_query(self, query: str) -> str:
        return self._chat(REWRITE_PROMPT.format(query=query))


class LLMFactory:
    @staticmethod
    def create(provider: str | None = None, model: str | None = None) -> ILLM:
        provider = (provider or settings.llm_provider or "mock").lower()
        model = model or settings.llm_model or None

        if provider == "openai":
            if not settings.openai_api_key:
                raise RuntimeError("OPENAI_API_KEY missing")
            return OpenAIProvider(settings.openai_api_key, model,
                                  settings.openai_base_url)
        if provider == "anthropic":
            if not settings.anthropic_api_key:
                raise RuntimeError("ANTHROPIC_API_KEY missing")
            return AnthropicProvider(settings.anthropic_api_key, model)
        if provider == "gemini":
            if not settings.google_api_key:
                raise RuntimeError("GOOGLE_API_KEY missing")
            return GeminiProvider(settings.google_api_key, model)
        if provider == "ollama":
            return OllamaProvider(settings.ollama_base_url, model)
        return MockProvider(model or "mock-vertex-gemini")

    @staticmethod
    def available() -> dict[str, bool]:
        return {
            "mock": True,
            "openai": bool(settings.openai_api_key),
            "anthropic": bool(settings.anthropic_api_key),
            "gemini": bool(settings.google_api_key),
            "ollama": True,
        }

    @staticmethod
    def active() -> dict[str, str]:
        try:
            inst = LLMFactory.create()
            return {"provider": inst.name,
                    "model": getattr(inst, "model", "")}
        except Exception as e:
            return {"provider": "mock", "model": "mock-vertex-gemini",
                    "error": str(e)}
