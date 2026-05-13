from dataclasses import dataclass, field, asdict
from datetime import datetime
from typing import Any


@dataclass
class Chunk:
    id: str
    doc_id: str
    text: str
    chunk_idx: int
    source: str
    char_start: int = 0
    char_end: int = 0
    metadata: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass
class RetrievalResult:
    chunk_id: str
    doc_id: str
    text: str
    source: str
    score: float
    rank: int
    strategy: str

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass
class ChatTurn:
    role: str
    content: str
    sources: list[dict] = field(default_factory=list)
    expanded_query: str = ""
    strategy: str = "A"
    latency_ms: float = 0.0
    timestamp: str = field(default_factory=lambda: datetime.utcnow().isoformat())

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)
