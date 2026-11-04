# MiniGPT Studio

A small multimodal assistant: one chat window that chats, draws and talks.

| Feature | How it works |
|---|---|
| Chat | Google Gemini API (streaming replies, conversation memory) |
| Draw | Hugging Face FLUX if `HF_TOKEN` is set, otherwise a free fallback service |
| Talk | edge-tts, free voices, no key needed |
| Routing | `router.py`: slash commands and keyword rules |

This app orchestrates pretrained models. It does not train a model.

## Run it

```bash
python -m venv venv
venv\Scripts\activate        # Windows  (macOS/Linux: source venv/bin/activate)
pip install -r requirements.txt
copy .env.example .env       # macOS/Linux: cp .env.example .env
# put your GEMINI_API_KEY in .env
streamlit run app.py
```

Get a free Gemini key at https://aistudio.google.com/apikey.

## Try

- `Explain photosynthesis in two lines`
- `draw a robot reading a book`
- `/say Welcome to my project`
- Turn on "Read replies aloud" in the sidebar

## Test

```bash
pytest
```

## Files

- `app.py` Streamlit UI
- `llm.py` chat model
- `image.py` text to image
- `tts.py` text to speech
- `router.py` picks chat, image or speech
