"""Text-to-speech using edge-tts (free, no API key)."""
import asyncio
import os
import re

import edge_tts

DEFAULT_VOICE = os.getenv("TTS_VOICE", "en-IN-NeerjaNeural")


def _clean(text: str) -> str:
    """Remove markdown symbols so they are not read out."""
    text = re.sub(r"[`*#_>]+", "", text)
    return re.sub(r"\s+", " ", text).strip()[:2000]


async def _synthesize(text: str, voice: str) -> bytes:
    audio = bytearray()
    async for chunk in edge_tts.Communicate(text, voice).stream():
        if chunk["type"] == "audio":
            audio.extend(chunk["data"])
    return bytes(audio)


def speak(text: str, voice: str | None = None) -> bytes:
    """Return MP3 bytes for the text."""
    text = _clean(text)
    if not text:
        raise ValueError("Nothing to read. Try '/say hello everyone'.")
    audio = asyncio.run(_synthesize(text, voice or DEFAULT_VOICE))
    if not audio:
        raise RuntimeError("Speech service returned no audio. Try again.")
    return audio
