"""NLP understanding layer: works out what the user means before anything is run.

One small LLM call returns structured JSON:
  intent        chat | search | image | speech
  query         the request rewritten as a clear standalone question (typos fixed, 'he/it' resolved)
  image_prompt  a vivid description for the image generator
  speak_text    the exact text to read aloud
  language      the language the user wrote in

The call is limited to NLP_TIMEOUT seconds. If it fails or is too slow, the old rule-based
router is used instead, so the app never breaks or waits long.
"""
import json
import os
import re
from concurrent.futures import ThreadPoolExecutor, TimeoutError as FutureTimeout
from dataclasses import dataclass, replace

import llm
import router
import search

INTENTS = {"chat", "search", "image", "speech"}
NLP_TIMEOUT = float(os.getenv("NLP_TIMEOUT", "8"))
_pool = ThreadPoolExecutor(max_workers=2)

SYSTEM = """You are the language-understanding layer of an assistant app.
Read the user's latest message (use the recent conversation for context) and return ONLY a JSON object with these keys:
"intent": one of
  "chat"   - general knowledge, explanations, coding, advice, maths, small talk
  "search" - needs current or real-world facts: who holds a position, news, prices, dates, institutions, contact details, anything that may have changed
  "image"  - the user wants a picture drawn or generated
  "speech" - the user wants some text read aloud or spoken
"query": the user's request rewritten as a clear standalone question or instruction, in the user's own language. Fix spelling. Replace words like "he", "she", "it", "that" using the conversation.
"image_prompt": if intent is image, a vivid English description for an image generator (subject, style, setting, lighting). Otherwise "".
"speak_text": if intent is speech, exactly the text to read aloud. Otherwise "".
"language": the language the user wrote in, for example "English", "Hindi", "Kannada".
Return JSON only, with no extra text."""


@dataclass
class Understanding:
    intent: str
    query: str
    image_prompt: str = ""
    speak_text: str = ""
    language: str = "English"
    source: str = "nlp"  # "nlp" or "rules"
    reason: str = ""  # why the rules were used instead of the NLP call


def rules(text: str) -> Understanding:
    """Fallback: slash commands, keyword routing and the search keyword rules."""
    mode, payload = router.route(text)
    if mode == "chat" and search.should_search(text):
        mode = "search"
    return Understanding(
        intent=mode,
        query=payload,
        image_prompt=payload if mode == "image" else "",
        speak_text=payload if mode == "speech" else "",
        language="English",
        source="rules",
    )


def _parse(raw: str) -> dict:
    raw = raw.strip()
    raw = re.sub(r"^```(?:json)?|```$", "", raw, flags=re.MULTILINE).strip()
    start, end = raw.find("{"), raw.rfind("}")
    if start == -1 or end == -1:
        raise ValueError("no JSON object in reply")
    return json.loads(raw[start : end + 1])


def understand(text: str, history: list[dict] | None = None) -> Understanding:
    """Return what the user wants. Never raises and never waits longer than NLP_TIMEOUT."""
    t = text.strip()
    if t.startswith("/"):  # explicit commands always win
        return rules(t)
    try:
        recent = (history or [])[-4:]
        ctx = "\n".join(f"{m['role']}: {m['content'][:300]}" for m in recent)
        user = f"Recent conversation:\n{ctx or '(none)'}\n\nLatest user message:\n{t}"
        future = _pool.submit(llm.complete_json, SYSTEM, user, 400, False)
        try:
            raw = future.result(timeout=NLP_TIMEOUT)
        except FutureTimeout:
            raise TimeoutError(f"took longer than {NLP_TIMEOUT:.0f}s")
        data = _parse(raw)

        intent = str(data.get("intent", "")).strip().lower()
        if intent not in INTENTS:
            raise ValueError(f"unknown intent {intent!r}")
        query = str(data.get("query") or t).strip() or t
        language = str(data.get("language") or "English").strip()[:30].title() or "English"
        return Understanding(
            intent=intent,
            query=query,
            image_prompt=str(data.get("image_prompt") or "").strip() or (query if intent == "image" else ""),
            speak_text=str(data.get("speak_text") or "").strip() or (query if intent == "speech" else ""),
            language=language,
            source="nlp",
        )
    except Exception as e:
        return replace(rules(t), reason=f"{type(e).__name__}: {str(e)[:80]}")