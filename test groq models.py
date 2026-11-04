from types import SimpleNamespace

import llm


class FakeCompletions:
    def __init__(self):
        self.calls = []

    def create(self, **kw):
        self.calls.append(kw["model"])
        if kw["model"] == "bad-model":
            raise RuntimeError("Error code: 404 - The model does not exist or you do not have access")
        if kw.get("stream"):
            chunk = SimpleNamespace(choices=[SimpleNamespace(delta=SimpleNamespace(content="hi"))])
            return iter([chunk])
        return SimpleNamespace(choices=[SimpleNamespace(message=SimpleNamespace(content='{"intent":"chat"}'))])


def fake_client(monkeypatch):
    comps = FakeCompletions()
    client = SimpleNamespace(chat=SimpleNamespace(completions=comps))
    monkeypatch.setattr(llm, "_groq", lambda: client)
    monkeypatch.setenv("GROQ_MODEL", "bad-model")
    monkeypatch.setenv("GROQ_FALLBACK_MODELS", "good-model")
    return comps


def test_stream_uses_backup_model_when_main_is_missing(monkeypatch):
    comps = fake_client(monkeypatch)
    assert "".join(llm._groq_stream([], "hello", None)) == "hi"
    assert comps.calls == ["bad-model", "good-model"]


def test_json_uses_backup_model_when_main_is_missing(monkeypatch):
    comps = fake_client(monkeypatch)
    assert llm._groq_json("s", "u", 100) == '{"intent":"chat"}'
    assert comps.calls == ["bad-model", "good-model"]


def test_model_list_removes_duplicates(monkeypatch):
    monkeypatch.setenv("GROQ_MODEL", "a")
    monkeypatch.setenv("GROQ_FALLBACK_MODELS", "a, b ,c,b")
    assert llm._groq_models() == ["a", "b", "c"]