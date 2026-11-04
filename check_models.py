"""Prints the Groq models your API key can use.

Run it from the project folder with the virtual environment active:
    python check_models.py
"""
import os

from dotenv import load_dotenv

load_dotenv()

from groq import Groq  # noqa: E402

key = os.getenv("GROQ_API_KEY")
if not key:
    raise SystemExit("GROQ_API_KEY was not found in .env")

ids = sorted(m.id for m in Groq(api_key=key).models.list().data)
print("Models available to your key:")
for model_id in ids:
    print("  ", model_id)
print()
print("GROQ_MODEL in your .env:", repr(os.getenv("GROQ_MODEL")) if os.getenv("GROQ_MODEL") else "(not set)")