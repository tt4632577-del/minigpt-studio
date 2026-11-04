"""Decides whether a message should be answered with chat, an image or speech."""
import re

IMAGE_PATTERN = re.compile(
    r"^\s*(draw|paint|sketch|illustrate"
    r"|(generate|create|make)\s+(an?\s+)?(image|picture|photo|drawing)"
    r"|show me (an?\s+)?(image|picture|photo) of)\b",
    re.IGNORECASE,
)


def route(text: str) -> tuple[str, str]:
    """Return (mode, payload) where mode is 'chat', 'image' or 'speech'.

    Slash commands always win:
      /image <prompt>  -> image
      /say <text>      -> speech
    Otherwise messages that start with a drawing request go to image generation,
    and everything else is a normal chat message.
    """
    t = text.strip()
    low = t.lower()
    if low.startswith("/image"):
        return "image", t[len("/image"):].strip()
    if low.startswith("/say"):
        return "speech", t[len("/say"):].strip()
    if IMAGE_PATTERN.match(t):
        return "image", t
    return "chat", t
