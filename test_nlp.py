import time

import llm
import nlp


def fake(monkeypatch, reply):
    def _fake(system, user, max_tokens=400, fallback=True):
        if isinstance(reply, Exception):
            raise reply
        return reply
    monkeypatch.setattr(llm, "complete_json", _fake)


def test_image_intent(monkeypatch):
    fake(monkeypatch, '{"intent":"image","query":"draw a cat","image_prompt":"A cat in sunglasses, cartoon style","speak_text":"","language":"english"}')
    u = nlp.understand("can u pls draw a cat wearing sunglasess")
    assert u.intent == "image"
    assert "sunglasses" in u.image_prompt
    assert u.language == "English"
    assert u.source == "nlp"


def test_search_with_followup_rewrite(monkeypatch):
    fake(monkeypatch, '{"intent":"search","query":"What is the email of the dean of the School of Information Science?","language":"English"}')
    u = nlp.understand("and his email?", [{"role": "user", "content": "who is the dean"}])
    assert u.intent == "search"
    assert "dean" in u.query


def test_json_in_code_fence(monkeypatch):
    fake(monkeypatch, '```json\n{"intent":"chat","query":"Explain DNS","language":"Hindi"}\n```')
    u = nlp.understand("DNS kya hai")
    assert u.intent == "chat" and u.language == "Hindi"


def test_speech_without_text_uses_query(monkeypatch):
    fake(monkeypatch, '{"intent":"speech","query":"Welcome everyone","language":"English"}')
    assert nlp.understand("read it out").speak_text == "Welcome everyone"


def test_bad_json_falls_back_to_rules(monkeypatch):
    fake(monkeypatch, "sorry, I cannot do that")
    u = nlp.understand("draw a cat")
    assert u.source == "rules" and u.intent == "image"
    assert u.reason


def test_unknown_intent_falls_back(monkeypatch):
    fake(monkeypatch, '{"intent":"dance","query":"x"}')
    assert nlp.understand("What is DNS?").source == "rules"


def test_llm_error_falls_back_with_reason(monkeypatch):
    fake(monkeypatch, RuntimeError("503"))
    u = nlp.understand("Who is the dean of the school of information science?")
    assert u.source == "rules" and u.intent == "search"
    assert "503" in u.reason


def test_slow_model_times_out_quickly(monkeypatch):
    def slow(system, user, max_tokens=400, fallback=True):
        time.sleep(1.5)
        return '{"intent":"chat","query":"x"}'

    monkeypatch.setattr(llm, "complete_json", slow)
    monkeypatch.setattr(nlp, "NLP_TIMEOUT", 0.2)
    start = time.perf_counter()
    u = nlp.understand("What is DNS?")
    assert time.perf_counter() - start < 1.0
    assert u.source == "rules" and "Timeout" in u.reason


def test_slash_command_skips_llm(monkeypatch):
    fake(monkeypatch, RuntimeError("should not be called"))
    u = nlp.understand("/say hello everyone")
    assert u.intent == "speech" and u.speak_text == "hello everyone"