"""Text-to-image with several providers, tried in order until one works.

Order: Gemini (if GEMINI_IMAGE_MODEL is set) -> Hugging Face (if HF_TOKEN is set) -> Pollinations (free, no key).
Each provider is skipped if it is not configured. If all fail, the error lists why.
"""
import io
import os
import time
import urllib.parse

import requests


# ---------------------------------------------------------------- Gemini
def _from_gemini(prompt: str) -> bytes:
    from google import genai
    from google.genai import types

    key = os.getenv("GEMINI_API_KEY")
    if not key:
        raise RuntimeError("GEMINI_API_KEY is missing")
    client = genai.Client(api_key=key)
    resp = client.models.generate_content(
        model=os.environ["GEMINI_IMAGE_MODEL"],
        contents=prompt,
        config=types.GenerateContentConfig(response_modalities=["TEXT", "IMAGE"]),
    )
    for cand in resp.candidates or []:
        for part in (cand.content.parts if cand.content else []):
            if getattr(part, "inline_data", None) and part.inline_data.data:
                return part.inline_data.data
    raise RuntimeError("Gemini returned no image (the model may not support images or refused the prompt)")


# ---------------------------------------------------------- Hugging Face
def _from_huggingface(prompt: str) -> bytes:
    from huggingface_hub import InferenceClient

    client = InferenceClient(api_key=os.environ["HF_TOKEN"])
    model = os.getenv("HF_IMAGE_MODEL", "black-forest-labs/FLUX.1-schnell")
    img = client.text_to_image(prompt, model=model)  # returns a PIL image
    buf = io.BytesIO()
    img.save(buf, format="PNG")
    return buf.getvalue()


# ------------------------------------------------------------ Pollinations
def _from_pollinations(prompt: str) -> bytes:
    url = "https://image.pollinations.ai/prompt/" + urllib.parse.quote(prompt)
    last = None
    for attempt in range(2):  # one retry, since 503 is often a short spike
        resp = requests.get(url, params={"width": 768, "height": 768}, timeout=90)
        if resp.status_code in (429, 502, 503):
            last = f"{resp.status_code} (busy)"
            time.sleep(3)
            continue
        if resp.status_code == 402:
            raise RuntimeError("402 (needs payment or login)")
        resp.raise_for_status()
        if not resp.headers.get("content-type", "").startswith("image"):
            raise RuntimeError("did not return an image")
        return resp.content
    raise RuntimeError(last or "unavailable")


def generate_image(prompt: str) -> bytes:
    """Return image bytes for the prompt."""
    prompt = prompt.strip()
    if not prompt:
        raise ValueError("Describe what to draw, e.g. 'draw a robot reading a book'.")

    providers = []
    if os.getenv("GEMINI_IMAGE_MODEL"):
        providers.append(("Gemini", _from_gemini))
    if os.getenv("HF_TOKEN"):
        providers.append(("Hugging Face", _from_huggingface))
    providers.append(("Pollinations", _from_pollinations))

    errors = []
    for name, fn in providers:
        try:
            return fn(prompt)
        except Exception as e:
            errors.append(f"{name}: {str(e).splitlines()[0][:160]}")
    raise RuntimeError("All image services failed. " + " | ".join(errors))