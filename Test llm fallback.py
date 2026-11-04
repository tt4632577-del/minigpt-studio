import pytest

import llm


def setup_env(monkeypatch, provider="gemini"):
    monkeypatch.setenv("LLM_PROVIDER", provider)
    monkeypatch.setenv("GEMINI_API_KEY", "x")
    monkeypatch.setenv("GROQ_API_KEY", "y")
    monkeypatch.setattr(llm.time, "sleep", lambda s: None)


def test_switches_to_groq_when_gemini_is_busy(monkeypatch):
    setup_env(monkeypatch)

    def busy(history, text, language):
        raise RuntimeError("503 UNAVAILABLE high demand")
        yield  # pragma: no cover

    def ok(history, text, language):
        yield "hello "
        yield "world"

    monkeypatch.setattr(llm, "_gemini_stream", busy)
    monkeypatch.setattr(llm, "_groq_stream", ok)
    assert "".join(llm.chat_stream([], "hi")) == "hello world"


def test_retries_same_provider_once_when_busy(monkeypatch):
    setup_env(monkeypatch)
    monkeypatch.delenv("GROQ_API_KEY")
    calls = {"n": 0}

    def flaky(history, text, language):
        calls["n"] += 1
        if calls["n"] == 1:
            raise RuntimeError("503 UNAVAILABLE")
        yield "ok"

    monkeypatch.setattr(llm, "_gemini_stream", flaky)
    assert "".join(llm.chat_stream([], "hi")) == "ok"
    assert calls["n"] == 2


def test_error_lists_all_providers(monkeypatch):
    setup_env(monkeypatch)

    def bad(history, text, language):
        raise RuntimeError("boom")
        yield  # pragma: no cover

    monkeypatch.setattr(llm, "_gemini_stream", bad)
    monkeypatch.setattr(llm, "_groq_stream", bad)
    with pytest.raises(RuntimeError) as e:
        list(llm.chat_stream([], "hi"))
    assert "gemini" in str(e.value) and "groq" in str(e.value)


def test_json_falls_back_to_other_provider(monkeypatch):
    setup_env(monkeypatch, provider="groq")
    monkeypatch.setattr(llm, "_groq_json", lambda s, u, m: (_ for _ in ()).throw(RuntimeError("down")))
    monkeypatch.setattr(llm, "_gemini_json", lambda s, u, m: '{"intent":"chat"}')
    assert llm.complete_json("s", "u") == '{"intent":"chat"}'


def test_only_main_provider_when_other_has_no_key(monkeypatch):
    setup_env(monkeypatch)
    monkeypatch.delenv("GROQ_API_KEY")
    assert llm._order() == ["gemini"]