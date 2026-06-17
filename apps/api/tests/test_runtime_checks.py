from types import SimpleNamespace

from app.config import settings
from app.intelligence.assist.rag import store
from app.runtime_checks import check_database_schema, check_llm


def test_chroma_url_uses_http_client(monkeypatch):
    calls = {}

    class FakeHttpClient:
        def __init__(self, host, port, ssl):
            calls["host"] = host
            calls["port"] = port
            calls["ssl"] = ssl

    monkeypatch.setattr(settings, "VECTOR_STORE", "chroma")
    monkeypatch.setattr(settings, "CHROMA_URL", "https://chroma.internal:8443")
    monkeypatch.setitem(
        __import__("sys").modules,
        "chromadb",
        SimpleNamespace(HttpClient=FakeHttpClient, PersistentClient=lambda path: None),
    )

    client = store.chroma_client()

    assert isinstance(client, FakeHttpClient)
    assert calls == {"host": "chroma.internal", "port": 8443, "ssl": True}


def test_sqlite_schema_check_is_limited_to_test_database():
    result = check_database_schema()
    assert result["ok"] is True
    assert result["database"] == "sqlite-test"


def test_openrouter_readiness_does_not_make_network_call(monkeypatch):
    monkeypatch.setattr(settings, "LLM_PROVIDER", "openrouter")
    monkeypatch.setattr(settings, "OPENROUTER_API_KEY", "test-key")
    monkeypatch.setattr(settings, "OPENROUTER_MODEL", "openrouter/free")
    monkeypatch.setattr(settings, "LLM_REQUIRED", True)

    result = check_llm()

    assert result["ok"] is True
    assert result["provider"] == "openrouter"
    assert result["configured"] is True
    assert result["model"] == "openrouter/free"
