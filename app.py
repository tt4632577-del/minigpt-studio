"""MiniGPT Studio: one chat window that understands, chats, searches the web, reads your documents,
draws and talks."""
import time

import streamlit as st
from dotenv import load_dotenv

load_dotenv()

import docs  # noqa: E402
import export  # noqa: E402
import feedback  # noqa: E402
import image  # noqa: E402
import llm  # noqa: E402
import nlp  # noqa: E402
import personas  # noqa: E402
import search  # noqa: E402
import tts  # noqa: E402
import ui  # noqa: E402

VOICES = ["en-IN-NeerjaNeural", "en-IN-PrabhatNeural", "en-US-AriaNeural", "hi-IN-SwaraNeural"]
LANG_VOICES = {
    "hindi": "hi-IN-SwaraNeural",
    "kannada": "kn-IN-SapnaNeural",
    "tamil": "ta-IN-PallaviNeural",
    "telugu": "te-IN-ShrutiNeural",
}
TRANSLATE_TO = [("ಕನ್ನಡ", "Kannada"), ("हिन्दी", "Hindi"), ("English", "English")]
DOC_TASKS = {
    "summary": (
        "Summarise the uploaded document",
        "Write a clear summary of the document in these passages: first one sentence on what it is about, "
        "then 5 to 8 bullet points with the key ideas.",
    ),
    "quiz": (
        "Make a quiz from the uploaded document",
        "Write 5 multiple-choice questions based on these passages. Give 4 options (A to D) for each. "
        "After all questions, give an answer key.",
    ),
}

st.set_page_config(page_title="MiniGPT Studio", page_icon=":printer:", layout="centered")
st.markdown(ui.css(), unsafe_allow_html=True)

if "messages" not in st.session_state:
    st.session_state.messages = []
queued = st.session_state.pop("queued", None)  # an example chosen on the welcome screen
task = None  # a document button pressed in the sidebar

with st.sidebar:
    st.header("Controls")
    mode = st.selectbox("Assistant mode", list(personas.PERSONAS))
    st.caption(personas.PERSONAS[mode]["blurb"])
    use_nlp = st.toggle(
        "Smart understanding", value=True,
        help="Uses the language model to understand your message, fix typos, follow up on earlier questions and detect your language.",
    )
    search_mode = st.selectbox(
        "Web search", ["Auto", "Always", "Off"],
        help="Auto lets the app decide. Always searches every question. Off never searches.",
    )
    auto_speak = st.toggle("Read replies aloud", value=False)
    voice = st.selectbox("Voice", VOICES)

    st.subheader("Your document")
    uploaded = st.file_uploader("PDF or text file", type=["pdf", "txt", "md"], label_visibility="collapsed")
    doc = st.session_state.get("doc")
    if uploaded is not None:
        sig = (uploaded.name, uploaded.size)
        if not doc or doc["sig"] != sig:
            with st.spinner("Reading the document..."):
                try:
                    pages = docs.extract_text(uploaded.name, uploaded.getvalue())
                    chunks = docs.chunk_pages(pages)
                    if not chunks:
                        raise ValueError("no readable text found (scanned PDFs are not supported)")
                    doc = {"sig": sig, "name": uploaded.name, "chunks": chunks,
                           "index": docs.DocIndex(chunks), "pages": len(pages)}
                except Exception as e:
                    doc = None
                    st.error(f"Could not read the document: {e}")
            st.session_state.doc = doc
    else:
        doc = st.session_state.doc = None
    use_doc = False
    if doc:
        st.caption(f"{doc['name']}: {doc['pages']} page(s), {len(doc['chunks'])} passages")
        use_doc = st.toggle("Answer from this document", value=True)
        if st.button("Summarise document", use_container_width=True):
            task = "summary"
        if st.button("Make a quiz", use_container_width=True):
            task = "quiz"

    if st.button("Clear chat"):
        st.session_state.messages = []
        st.rerun()
    if st.session_state.messages:
        st.download_button(
            "Download chat", export.chat_to_markdown(st.session_state.messages),
            file_name="minigpt_chat.md", mime="text/markdown",
        )
    with st.expander("Feedback statistics"):
        s = feedback.stats()
        if s["total"]:
            st.write(f"Rated replies: **{s['total']}**  |  Helpful: **{round(100 * s['up'] / s['total'])}%**")
            for p, secs in s["by_provider"].items():
                st.write(f"{p}: average {secs:.1f}s")
        else:
            st.caption("No ratings yet. Use the thumbs under a reply.")
    st.markdown(ui.legend(), unsafe_allow_html=True)
    st.caption("AI can make mistakes. Check important facts in the sources.")


def voice_for(language: str) -> str:
    return LANG_VOICES.get((language or "").lower(), voice)


def translate(text: str, language: str) -> str:
    request = f"Translate the following text into {language}. Reply with only the translation.\n\n{text}"
    return "".join(llm.chat_stream([], request, None, language)).strip()


def welcome() -> None:
    st.markdown(ui.hero(), unsafe_allow_html=True)
    for row in (ui.PADS[:2], ui.PADS[2:]):
        cols = st.columns(2, gap="large")
        for col, (intent, description, example) in zip(cols, row):
            with col:
                with st.container(key=f"pad_{intent}"):
                    st.markdown(ui.pad_head(intent, description), unsafe_allow_html=True)
                    if st.button(example, key=f"try_{intent}"):
                        st.session_state.queued = example
                        st.rerun()
    st.markdown(ui.hint(), unsafe_allow_html=True)


def rate(msg: dict, value: str) -> None:
    msg["rating"] = value
    seconds = sum(t for _, t in msg.get("stages", []))
    try:
        feedback.log(msg.get("mode", "General"), msg.get("intent", "chat"), msg.get("provider", ""), seconds, value)
    except OSError:
        pass  # a read-only folder should never break the chat


def render(msg: dict, idx: int) -> None:
    with st.chat_message(msg["role"]):
        if msg["role"] == "user":
            st.markdown(msg["content"])
            return
        intent = msg.get("intent", "chat")
        st.markdown(
            ui.header(intent, msg.get("language", "English"), msg.get("interpreted", ""), msg.get("note", "")),
            unsafe_allow_html=True,
        )
        if msg["kind"] == "image":
            st.image(msg["image"], caption=msg["content"])
            st.download_button("Download image", msg["image"], file_name=f"image_{idx}.png",
                               mime="image/png", key=f"dl{idx}")
        else:
            st.markdown(msg["content"])
            if msg.get("sources"):
                st.markdown(ui.sources(msg["sources"]), unsafe_allow_html=True)
            if msg.get("doc_note"):
                st.caption(msg["doc_note"])
            for lang, text in msg.get("translations", {}).items():
                st.markdown(f"**{lang}:** {text}")
            if msg.get("audio"):
                st.audio(msg["audio"], format="audio/mp3")
            if msg["kind"] == "text":
                cols = st.columns(6)
                if not msg.get("audio") and cols[0].button("Listen", key=f"ra{idx}"):
                    try:
                        msg["audio"] = tts.speak(msg["content"], voice_for(msg.get("language", "English")))
                        st.rerun()
                    except Exception as e:
                        st.error(f"Could not read aloud: {e}")
                if not msg.get("rating"):
                    if cols[1].button("👍", key=f"up{idx}"):
                        rate(msg, "up")
                        st.rerun()
                    if cols[2].button("👎", key=f"down{idx}"):
                        rate(msg, "down")
                        st.rerun()
                else:
                    cols[1].caption("Thanks!")
                for col, (label, language) in zip(cols[3:], TRANSLATE_TO):
                    if language not in msg.get("translations", {}) and col.button(label, key=f"tr{language}{idx}"):
                        with st.spinner("Translating..."):
                            try:
                                msg.setdefault("translations", {})[language] = translate(msg["content"], language)
                                st.rerun()
                            except Exception as e:
                                st.error(f"Could not translate: {e}")
        if msg.get("stages"):
            st.markdown(ui.strip(intent, msg["stages"], msg.get("provider", "")), unsafe_allow_html=True)


pending = queued
if task and doc:
    pending = DOC_TASKS[task][0]

if st.session_state.messages:
    for i, m in enumerate(st.session_state.messages):
        render(m, i)
elif not pending:
    welcome()

prompt = st.chat_input("Ask anything. Typos and follow-ups are fine.") or pending
if prompt:
    history = [
        {"role": m["role"], "content": m["content"]}
        for m in st.session_state.messages
        if m["kind"] == "text"
    ]
    st.session_state.messages.append({"role": "user", "kind": "text", "content": prompt})
    with st.chat_message("user"):
        st.markdown(prompt)

    reply = None
    with st.chat_message("assistant"):
        try:
            t0 = time.perf_counter()
            doc_job = task if (task and doc and prompt == DOC_TASKS[task][0]) else None
            if doc_job:
                u = nlp.Understanding(intent="chat", query=DOC_TASKS[doc_job][1], language="English", source="rules")
            elif use_nlp:
                with st.spinner("Understanding..."):
                    u = nlp.understand(prompt, history)
            else:
                u = nlp.rules(prompt)
            stages = [("Understood", time.perf_counter() - t0)]

            interpreted = ""
            if not doc_job and u.intent in ("chat", "search") and u.query.strip().lower() != prompt.strip().lower():
                interpreted = u.query
            note = f"Basic rules were used: {u.reason}" if (u.source == "rules" and use_nlp and u.reason) else ""
            st.markdown(ui.header(u.intent, u.language, interpreted, note), unsafe_allow_html=True)
            base = {"role": "assistant", "intent": u.intent, "language": u.language,
                    "interpreted": interpreted, "note": note, "mode": mode}

            if u.intent == "image":
                t0 = time.perf_counter()
                with st.spinner("Drawing..."):
                    img = image.generate_image(u.image_prompt or u.query)
                stages.append(("Drew", time.perf_counter() - t0))
                reply = {**base, "kind": "image", "content": u.image_prompt or u.query,
                         "image": img, "stages": stages}
            elif u.intent == "speech":
                t0 = time.perf_counter()
                with st.spinner("Recording speech..."):
                    audio = tts.speak(u.speak_text or u.query, voice_for(u.language))
                stages.append(("Spoke", time.perf_counter() - t0))
                reply = {**base, "kind": "speech", "content": u.speak_text or u.query,
                         "audio": audio, "stages": stages}
            else:
                sources, web_sources, doc_note = [], [], ""
                if doc_job:
                    picked = docs.overview(doc["chunks"])
                    sources = docs.as_sources(doc["name"], picked)
                    doc_note = f"Based on {len(picked)} passages spread across {doc['name']}."
                elif use_doc and doc:
                    t0 = time.perf_counter()
                    hits = doc["index"].search(u.query)
                    if hits:
                        sources = docs.as_sources(doc["name"], hits)
                        doc_note = "From your document: " + ", ".join(h["label"] for h in hits)
                        stages.append(("Read document", time.perf_counter() - t0))
                if not sources and search_mode != "Off" and (u.intent == "search" or search_mode == "Always"):
                    t0 = time.perf_counter()
                    with st.spinner("Searching the web..."):
                        try:
                            web_sources = sources = search.web_search(u.query)
                        except Exception as e:
                            st.warning(f"Web search failed, answering without it: {e}")
                    stages.append(("Searched", time.perf_counter() - t0))
                t0 = time.perf_counter()
                question = u.query if doc_job else personas.wrap(mode, u.query)
                text = st.write_stream(llm.chat_stream(history, question, sources, u.language))
                stages.append(("Answered", time.perf_counter() - t0))
                reply = {**base, "kind": "text", "content": text, "sources": web_sources,
                         "doc_note": doc_note, "stages": stages, "provider": llm.LAST_PROVIDER}
                if auto_speak and text:
                    reply["audio"] = tts.speak(text, voice_for(u.language))
        except Exception as e:
            st.error(f"Something went wrong: {e}")

    if reply:
        st.session_state.messages.append(reply)
        st.rerun()