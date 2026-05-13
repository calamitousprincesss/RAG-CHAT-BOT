from __future__ import annotations
from app.Services.interfaces import ILLM
from app.Services.llm_provider import LLMFactory


class QueryExpander:
    def __init__(self, llm: ILLM | None = None):
        self._llm = llm or LLMFactory.create()

    def expand(self, query: str) -> str:
        try:
            return self._llm.rewrite_query(query).strip() or query
        except Exception:
            return query
