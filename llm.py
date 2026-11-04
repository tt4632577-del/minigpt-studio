"""Chat model wrapper. Supports Google Gemini and Groq (very fast open models).

LLM_PROVIDER in .env picks the main one: gemini (default) or groq.
If the main provider is overloaded or fails, the other one is used automatically
(when its API key is in .env), so a temporary 503 does not reach the user.
Inside Groq, if the chosen model does not exist for your key, backup models are tried.
Every call has a time limit (LLM_TIMEOUT seconds) so nothing can hang for minutes.

Optionally pass web search results as `sources` so answers are grounded in them,
and a `language` so the reply is written in the user's language.
"""
import datetime
import os
import time
from typing import Iterator

BASE_PROMPT = (
    "You are a friendly, concise AI assistant inside a small multimodal app. "
    "Answer any question the user asks on any topic. "
    "Be accurate, and say so when you are not sure. "
    "Keep replies short unless the user asks for detail."
)

MAX_HISTORY = 8  # only the last few messages are sent, which keeps replies fast
KEY_NAMES = {"gemini": "GEMINI_API_KEY", "groq": "GROQ_API_KEY"}
BUSY_WORDS = ("503", "unavailable", "overloaded", "high demand", "429", "rate")
GROQ_FALLBACKS = "openai/gpt-oss-20b,openai/gpt-oss-120b,llama-3.1-8b-instant"
LAST_PROVIDER = ""  # which provider answered most recently, shown in the UI


def _timeout() -> float:
    return float(os.getenv("LLM_TIMEOUT", "20"))


def _system(language: str | None = None) -> str:
    if language and language.strip().lower() != "english":
        return f"{BASE_PROMPT} Reply in {language}."
    return BASE_PROMPT


def _provider() -> str:
    return os.getenv("LLM_PROVIDER", "gemini").strip().lower()


def _order() -> list[str]:
    """Main provider first, then the other one if it has a key."""
    main = "groq" if _provider() == "groq" else "gemini"
    other = "gemini" if main == "groq" else "groq"
    order = [main]
    if os.getenv(KEY_NAMES[other]):
        order.append(other)
    return order


def _is_busy(err: Exception) -> bool:
    text = str(err).lower()
    return any(w in text for w in BUSY_WORDS)


def _is_model_error(err: Exception) -> bool:
    text = str(err).lower()
    return any(w in text for w in ("404", "does not exist", "model_not_found", "decommissioned"))


def _with_sources(user_text: str, sources: list[dict] | None) -> str:
    """Wrap the question with web results so the model answers from them."""
    if not sources:
        return user_text
    block = "\n\n".join(
        f"[{i}] {s['title']} ({s['url']})\n{s['snippet']}" for i, s in enumerate(sources, 1)
    )
    return (
        f"Today's date: {datetime.date.today().isoformat()}\n\n"
        f"Web search results:\n{block}\n\n"
        "Answer the question below using these results for any facts. "
        "Cite the sources you used as [1], [2]. "
        "If the results do not clearly answer it, say you could not confirm it instead of guessing. "
        "If results conflict or look out of date, say so.\n\n"
        f"Question: {user_text}"
    )


# ---------------------------------------------------------------- Gemini
_gemini_client = None


def _gemini() -> "genai.Client":
    global _gemini_client
    if _gemini_client is None:
        from google import genai
        from google.genai import types

        key = os.getenv("GEMINI_API_KEY")
        if not key:
            raise RuntimeError("GEMINI_API_KEY is missing. Add it to .env.")
        try:
            _gemini_client = genai.Client(
                api_key=key, http_options=types.HttpOptions(timeout=int(_timeout() * 1000))
            )
        except Exception:
            _gemini_client = genai.Client(api_key=key)
    return _gemini_client


def _gemini_stream(history: list[dict], user_text: str, language: str | None) -> Iterator[str]:
    from google.genai import types

    contents = []
    for m in history[-MAX_HISTORY:]:
        role = "user" if m["role"] == "user" else "model"
        contents.append(types.Content(role=role, parts=[types.Part(text=m["content"])]))
    contents.append(types.Content(role="user", parts=[types.Part(text=user_text)]))

    stream = _gemini().models.generate_content_stream(
        model=os.getenv("GEMINI_MODEL", "gemini-3.8-flash"),
        contents=contents,
        config=types.GenerateContentConfig(
            system_instruction=_system(language),
            max_output_tokens=int(os.getenv("MAX_OUTPUT_TOKENS", "800")),
        ),
    )
    for chunk in stream:
        if chunk.text:
            yield chunk.text


def _gemini_json(system: str, user: str, max_tokens: int) -> str:
    from google.genai import types

    resp = _gemini().models.generate_content(
        model=os.getenv("GEMINI_MODEL", "gemini-3.8-flash"),
        contents=user,
        config=types.GenerateContentConfig(
            system_instruction=system,
            response_mime_type="application/json",
            temperature=0,
            max_output_tokens=max(max_tokens, 1000),  # room for models that think first
        ),
    )
    return resp.text or ""


# ------------------------------------------------------------------ Groq
_groq_client = None


def _groq() -> "Groq":
    global _groq_client
    if _groq_client is None:
        from groq import Groq

        key = os.getenv("GROQ_API_KEY")
        if not key:
            raise RuntimeError("GROQ_API_KEY is missing. Add it to .env.")
        _groq_client = Groq(api_key=key, timeout=_timeout(), max_retries=0)
    return _groq_client


def _groq_models() -> list[str]:
    """The model from .env first, then backups, with duplicates removed."""
    main = os.getenv("GROQ_MODEL", "llama-3.3-70b-versatile").strip()
    extra = os.getenv("GROQ_FALLBACK_MODELS", GROQ_FALLBACKS).split(",")
    models = [main]
    for m in (e.strip() for e in extra):
        if m and m not in models:
            models.append(m)
    return models


def _groq_create(model: str, **kw):
    """Call Groq. The gpt-oss models think first, so ask them to think briefly to stay fast."""
    extra = {"reasoning_effort": "low"} if model.startswith("openai/gpt-oss") else {}
    try:
        return _groq().chat.completions.create(model=model, **kw, **extra)
    except TypeError:  # older groq package without reasoning_effort
        return _groq().chat.completions.create(model=model, **kw)


def _groq_stream(history: list[dict], user_text: str, language: str | None) -> Iterator[str]:
    messages = [{"role": "system", "content": _system(language)}]
    for m in history[-MAX_HISTORY:]:
        messages.append({"role": m["role"], "content": m["content"]})
    messages.append({"role": "user", "content": user_text})

    last = None
    for model in _groq_models():
        try:
            stream = _groq_create(
                model,
                messages=messages,
                stream=True,
                max_tokens=int(os.getenv("MAX_OUTPUT_TOKENS", "800")),
            )
        except Exception as e:
            if _is_model_error(e):
                last = e  # this model is not available to the key, try the next one
                continue
            raise
        for chunk in stream:
            piece = chunk.choices[0].delta.content
            if piece:
                yield piece
        return
    raise last or RuntimeError("no Groq model available")


def _groq_json(system: str, user: str, max_tokens: int) -> str:
    last = None
    for model in _groq_models():
        try:
            resp = _groq_create(
                model,
                messages=[{"role": "system", "content": system}, {"role": "user", "content": user}],
                response_format={"type": "json_object"},
                temperature=0,
                max_tokens=max(max_tokens, 800),  # room for models that think first
            )
            return resp.choices[0].message.content or ""
        except Exception as e:
            if _is_model_error(e):
                last = e
                continue
            raise
    raise last or RuntimeError("no Groq model available")


# ---------------------------------------------------------------- public
def chat_stream(
    history: list[dict],
    user_text: str,
    sources: list[dict] | None = None,
    language: str | None = None,
) -> Iterator[str]:
    """Yield the reply in chunks. Retries once if busy, then tries the other provider."""
    global LAST_PROVIDER
    prompt = _with_sources(user_text, sources)
    streams = {"gemini": _gemini_stream, "groq": _groq_stream}
    errors = []
    for name in _order():
        for attempt in range(2):
            started = False
            try:
                for piece in streams[name](history, prompt, language):
                    if not started:
                        LAST_PROVIDER = name
                    started = True
                    yield piece
                return
            except Exception as e:
                if started:
                    raise  # failed half-way through a reply; cannot switch silently
                errors.append(f"{name}: {str(e)[:120]}")
                if attempt == 0 and _is_busy(e):
                    time.sleep(1.0)
                    continue
                break
    raise RuntimeError("No chat model is available right now. " + " | ".join(errors))


def complete_json(system: str, user: str, max_tokens: int = 400, fallback: bool = True) -> str:
    """One non-streaming call that returns JSON text. Used by the NLP layer.

    With fallback=False only the main provider is tried, which keeps the call fast.
    """
    calls = {"gemini": _gemini_json, "groq": _groq_json}
    names = _order() if fallback else _order()[:1]
    errors = []
    for name in names:
        try:
            return calls[name](system, user, max_tokens)
        except Exception as e:
            errors.append(f"{name}: {str(e)[:120]}")
    raise RuntimeError(" | ".join(errors))