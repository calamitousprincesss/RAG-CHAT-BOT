from __future__ import annotations
from contextlib import contextmanager
from app.Config.settings import settings

_client = None
_enabled = False


def _init():
    global _client, _enabled
    if _client is not None or _enabled:
        return
    if not (settings.langfuse_public_key and settings.langfuse_secret_key):
        return
    try:
        from langfuse import Langfuse
        _client = Langfuse(
            public_key=settings.langfuse_public_key,
            secret_key=settings.langfuse_secret_key,
            host=settings.langfuse_host,
        )
        _enabled = True
    except Exception:
        _enabled = False


def is_enabled() -> bool:
    _init()
    return _enabled


@contextmanager
def trace(name: str, **metadata):
    _init()
    if not _enabled:
        yield None
        return
    try:
        tr = _client.trace(name=name, metadata=metadata)
        yield tr
    except Exception:
        yield None


@contextmanager
def span(trace_obj, name: str, **kwargs):
    if trace_obj is None:
        yield None
        return
    try:
        sp = trace_obj.span(name=name, **kwargs)
        yield sp
        sp.end()
    except Exception:
        yield None
