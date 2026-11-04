"""Look and feel for MiniGPT Studio: dark "four-colour press" themes.

Each mode has its own ink colour: chat, search, draw and speak. Pick a theme in the sidebar.
Every colour is set explicitly in CSS, so the page looks the same whatever theme the browser or
Streamlit is using. Every piece of dynamic text is escaped.
"""
import html
from urllib.parse import urlparse

# intent -> (English name, Kannada name)
MODES = {
    "chat": ("Chat", "ಮಾತು"),
    "search": ("Search", "ಹುಡುಕು"),
    "image": ("Draw", "ಚಿತ್ರ"),
    "speech": ("Speak", "ಧ್ವನಿ"),
}
INK_ORDER = ["chat", "image", "speech", "search"]

# intent, one-line description, example prompt shown on the welcome screen
PADS = [
    ("chat", "Explain, write, code or just talk.", "Explain DNS in two lines"),
    ("search", "Looks up the web and shows its sources.",
     "Who is the dean of the School of Information Science at Presidency University Bengaluru?"),
    ("image", "Turns your words into a picture.", "Draw a 90s cassette player in bold print colours"),
    ("speech", "Reads any text aloud, in your language.", "Read this out: Welcome to my project"),
]

# bg = page, card = panels and inputs, card2 = hover and user messages, ink = text, line = borders
THEMES = {
    "Midnight press": dict(bg="#0E1020", card="#161A31", card2="#212647", ink="#ECEAF4", line="#454C7E",
                           chat="#2CC4F4", search="#EDE9DC", image="#FF5DA2", speech="#FFC93C"),
    "Aurora": dict(bg="#071619", card="#0E2327", card2="#173A40", ink="#E4F4F0", line="#34666F",
                   chat="#3DDBB5", search="#8AB4FF", image="#FF8F70", speech="#FFD36B"),
    "Plum": dict(bg="#170E20", card="#22152F", card2="#33204A", ink="#F3EAF8", line="#69488A",
                 chat="#C79BFF", search="#7DD3FC", image="#FF7A98", speech="#FDE05C"),
    "Moss": dict(bg="#11140D", card="#1A1F14", card2="#283020", ink="#EEF0E1", line="#556640",
                 chat="#A5DB63", search="#E8E5D0", image="#FF8461", speech="#F6C84B"),
}
THEME_NAMES = list(THEMES)
DARK_TEXT = "#0B0D18"


# ------------------------------------------------------------ colour helpers
def _rgb(hex_color: str):
    return [int(hex_color[i:i + 2], 16) for i in (1, 3, 5)]


def _lum(hex_color: str) -> float:
    def f(c):
        c /= 255
        return c / 12.92 if c <= 0.03928 else ((c + 0.055) / 1.055) ** 2.4
    r, g, b = (f(c) for c in _rgb(hex_color))
    return 0.2126 * r + 0.7152 * g + 0.0722 * b


def contrast(a: str, b: str) -> float:
    """WCAG contrast ratio between two #rrggbb colours."""
    la, lb = _lum(a), _lum(b)
    return (max(la, lb) + 0.05) / (min(la, lb) + 0.05)


def blend(fg: str, bg: str, alpha: float) -> str:
    out = [round(f * alpha + b * (1 - alpha)) for f, b in zip(_rgb(fg), _rgb(bg))]
    return "#" + "".join(f"{v:02X}" for v in out)


def on_color(color: str) -> str:
    """Text colour (dark or white) that reads best on the given fill."""
    return DARK_TEXT if contrast(color, DARK_TEXT) >= contrast(color, "#FFFFFF") else "#FFFFFF"


def muted(theme: dict) -> str:
    return blend(theme["ink"], theme["bg"], 0.74)


def _vars(theme: dict) -> str:
    lines = [
        f"--bg:{theme['bg']};", f"--card:{theme['card']};", f"--card2:{theme['card2']};",
        f"--ink:{theme['ink']};", f"--muted:{muted(theme)};", f"--line:{theme['line']};",
        f"--link:{theme['chat']};",
    ]
    for intent in MODES:
        lines.append(f"--c-{intent}:{theme[intent]};")
        lines.append(f"--on-{intent}:{on_color(theme[intent])};")
    return ":root{" + "".join(lines) + "}"


IMPORT = (
    "@import url('https://fonts.googleapis.com/css2?family=Archivo:wdth,wght@62..125,100..900"
    "&family=Noto+Sans+Kannada:wght@400;600;700&family=Noto+Sans+Devanagari:wght@400;600;700&display=swap');"
    ":root{--font:'Archivo','Noto Sans Kannada','Noto Sans Devanagari',system-ui,sans-serif;}"
)

BASE = """
/* page: every colour is set here, so the browser or system theme cannot make text invisible */
html, body, .stApp, [data-testid="stAppViewContainer"], [data-testid="stMain"],
header[data-testid="stHeader"] { background: var(--bg) !important; }
.stApp, .stApp :is(p, span, label, li, div, small, summary, h1, h2, h3, h4, h5, h6, td, th, code) { color: var(--ink); }
.stApp, [data-testid="stMarkdownContainer"], [data-testid="stMarkdownContainer"] p,
[data-testid="stMarkdownContainer"] li, [data-testid="stChatInput"] textarea,
.stButton button, [data-testid="stSidebar"] label, [data-testid="stSidebar"] p { font-family: var(--font); }
[data-testid="stMainBlockContainer"], .block-container { max-width: 800px; padding-top: 2.2rem; }
[data-testid="stToolbar"], [data-testid="stDecoration"], #MainMenu, footer { display: none !important; }
[data-testid="stMarkdownContainer"] p { line-height: 1.65; }
[data-testid="stMarkdownContainer"] a { color: var(--link) !important; }
[data-testid="stMarkdownContainer"] code, .stApp pre { background: var(--card2) !important; border-radius: 3px; }

/* sidebar */
[data-testid="stSidebar"], [data-testid="stSidebarContent"] { background: var(--card) !important; }
[data-testid="stSidebar"] { border-right: 2px solid var(--line); }
[data-testid="stSidebar"] h2 { font-family: var(--font); font-stretch: 125%; font-weight: 800; font-size: 1.1rem; }

/* dropdowns (the open list is drawn outside the app, so it is styled globally) */
[data-baseweb="select"] > div { background: var(--card2) !important; border: 1.5px solid var(--line) !important; border-radius: 3px; }
[data-baseweb="select"] :is(div, span, input) { color: var(--ink) !important; }
[data-baseweb="select"] svg { fill: var(--ink) !important; }
[data-baseweb="popover"], [data-baseweb="popover"] :is(ul, li, div) { background: var(--card) !important; color: var(--ink) !important; }
[data-baseweb="popover"] li:hover, [data-baseweb="popover"] [aria-selected="true"] { background: var(--card2) !important; }

/* welcome screen */
[data-testid="stMarkdownContainer"] .hero-title {
  font-family: var(--font); font-stretch: 125%; font-weight: 900;
  font-size: clamp(2.3rem, 7vw, 3.9rem); line-height: 1; letter-spacing: -0.01em;
  margin: 0.4rem 0 0.9rem; padding: 0; color: var(--ink);
}
[data-testid="stMarkdownContainer"] .hero-sub { font-size: 1.1rem; max-width: 34rem; margin: 0 0 2rem; color: var(--muted); }
.swatches { display: flex; gap: 6px; }
.sw { width: 1.1rem; height: 1.1rem; border: 2px solid var(--ink); display: inline-block; }
.sw.chat, .ink.chat.on { background: var(--c-chat); } .sw.image, .ink.image.on { background: var(--c-image); }
.sw.speech, .ink.speech.on { background: var(--c-speech); } .sw.search, .ink.search.on { background: var(--c-search); }
.pad-head { display: flex; align-items: baseline; gap: 0.7rem; margin-bottom: 0.2rem; }
.pad-name { font-stretch: 125%; font-weight: 800; font-size: 1.35rem; }
.pad-kn { font-size: 1.05rem; color: var(--muted) !important; }
[data-testid="stMarkdownContainer"] .pad-desc { margin: 0 0 0.9rem; color: var(--muted); }
[data-testid="stMarkdownContainer"] .hint { margin-top: 1.6rem; font-size: 0.92rem; color: var(--muted); }

[class*="st-key-pad_"] {
  background: var(--card); border: 2px solid var(--line); border-radius: 3px;
  padding: 1.1rem 1.25rem 1.2rem; margin-bottom: 0.9rem; gap: 0.2rem;
}
.st-key-pad_chat { box-shadow: 6px 6px 0 var(--c-chat); }
.st-key-pad_search { box-shadow: 6px 6px 0 var(--c-search); }
.st-key-pad_image { box-shadow: 6px 6px 0 var(--c-image); }
.st-key-pad_speech { box-shadow: 6px 6px 0 var(--c-speech); }
[class*="st-key-try_"] button {
  background: transparent !important; border: none !important; padding: 0 0 2px !important;
  text-align: left; justify-content: flex-start; min-height: 0; font-weight: 600;
  border-bottom: 3px solid var(--ink) !important; border-radius: 0 !important; line-height: 1.4;
}
[class*="st-key-try_"] button p { color: var(--ink) !important; }
.st-key-try_chat button { border-bottom-color: var(--c-chat) !important; }
.st-key-try_search button { border-bottom-color: var(--c-search) !important; }
.st-key-try_image button { border-bottom-color: var(--c-image) !important; }
.st-key-try_speech button { border-bottom-color: var(--c-speech) !important; }
[class*="st-key-try_"] button:hover { background: var(--card2) !important; }

/* conversation: no bubbles, no avatars; replies sit on a coloured margin rule */
[data-testid="stChatMessage"] {
  background: transparent !important; border-left: 4px solid transparent; padding: 0.2rem 0 1.1rem 1rem; gap: 0;
}
[data-testid="stChatMessageAvatarUser"], [data-testid="stChatMessageAvatarAssistant"],
[data-testid="stChatMessageAvatarCustom"] { display: none; }
[data-testid="stChatMessage"]:has([data-testid="stChatMessageAvatarUser"]) {
  background: var(--card2) !important; border-left: none; border-radius: 3px; padding: 0.7rem 1rem; margin-bottom: 0.6rem;
}
[data-testid="stChatMessage"]:has([data-testid="stChatMessageAvatarUser"]) p { font-weight: 600; margin: 0; }
[data-testid="stChatMessage"]:has(.mk-chat) { border-left-color: var(--c-chat); }
[data-testid="stChatMessage"]:has(.mk-search) { border-left-color: var(--c-search); }
[data-testid="stChatMessage"]:has(.mk-image) { border-left-color: var(--c-image); }
[data-testid="stChatMessage"]:has(.mk-speech) { border-left-color: var(--c-speech); }
[data-testid="stChatMessage"] img { border: 2px solid var(--line); border-radius: 2px; }

.tab { display: inline-flex; align-items: baseline; gap: 0.6rem; padding: 0.15rem 0.7rem; margin-bottom: 0.5rem;
  font-size: 0.88rem; border-radius: 2px; }
.tab b { font-stretch: 125%; font-weight: 800; }
.stApp .tab.t-chat, .stApp .tab.t-chat * { background: var(--c-chat); color: var(--on-chat); }
.stApp .tab.t-search, .stApp .tab.t-search * { background: var(--c-search); color: var(--on-search); }
.stApp .tab.t-image, .stApp .tab.t-image * { background: var(--c-image); color: var(--on-image); }
.stApp .tab.t-speech, .stApp .tab.t-speech * { background: var(--c-speech); color: var(--on-speech); }
.tab .lang { opacity: 0.85; }
[data-testid="stMarkdownContainer"] .read-as { font-size: 0.86rem; color: var(--muted); margin: 0 0 0.5rem; }

/* sources as chips */
.srcs { display: flex; flex-wrap: wrap; gap: 0.5rem; margin: 0.6rem 0 0.2rem; }
[data-testid="stMarkdownContainer"] .srcs a { display: inline-flex; gap: 0.45rem; align-items: baseline; padding: 0.15rem 0.6rem;
  border: 1.5px solid var(--line); border-radius: 2px; color: var(--ink) !important; text-decoration: none; font-size: 0.82rem; background: var(--card); }
[data-testid="stMarkdownContainer"] .srcs a:hover { background: var(--ink); color: var(--bg) !important; }
.srcs a b { font-weight: 800; }

/* the colour control strip */
.strip { display: flex; align-items: center; flex-wrap: wrap; gap: 0.4rem 1.1rem; margin-top: 0.9rem;
  font-size: 0.8rem; color: var(--muted); font-variant-numeric: tabular-nums; }
.strip .stage { color: var(--muted); }
.inks { display: inline-flex; gap: 3px; }
.ink { width: 0.95rem; height: 0.95rem; border: 1.5px solid var(--ink); display: inline-block; }
.strip .stage b { font-weight: 800; color: var(--ink); }
.stage + .stage { border-left: 1.5px solid var(--line); padding-left: 1.1rem; }

/* controls */
.stButton button, .stDownloadButton button { border: 2px solid var(--line); border-radius: 3px; background: transparent; font-weight: 600; }
.stButton button:hover, .stDownloadButton button:hover { background: var(--ink); border-color: var(--ink); }
.stButton button:hover p, .stDownloadButton button:hover p { color: var(--bg) !important; }
button:focus-visible, a:focus-visible { outline: 3px solid var(--c-chat); outline-offset: 2px; }
[data-testid="stBottom"], [data-testid="stBottom"] > div, [data-testid="stBottomBlockContainer"] { background: var(--bg) !important; }
[data-testid="stChatInput"], [data-testid="stChatInput"] > div, [data-testid="stChatInput"] textarea {
  background: var(--card) !important; color: var(--ink) !important; }
[data-testid="stChatInput"] { border: 2px solid var(--line); border-radius: 3px; }
[data-testid="stChatInput"]:focus-within { border-color: var(--c-chat); }
[data-testid="stChatInput"] textarea::placeholder { color: var(--muted) !important; opacity: 1; }
[data-testid="stChatInput"] button { background: var(--c-chat) !important; border-radius: 2px; }
[data-testid="stChatInput"] button svg { fill: var(--on-chat) !important; color: var(--on-chat) !important; }
.legend { display: grid; grid-template-columns: auto 1fr; gap: 0.35rem 0.7rem; align-items: center; font-size: 0.85rem; margin-top: 0.6rem; }
"""


def css(theme: str = "") -> str:
    palette = THEMES.get(theme) or THEMES[THEME_NAMES[0]]
    return f"<style>{IMPORT}{_vars(palette)}{BASE}</style>"


def _e(text) -> str:
    return html.escape(str(text), quote=True)


def hero() -> str:
    swatches = "".join(f'<i class="sw {i}"></i>' for i in INK_ORDER)
    return (
        f'<div class="swatches" aria-hidden="true">{swatches}</div>'
        '<h1 class="hero-title">MiniGPT Studio</h1>'
        '<p class="hero-sub">Say it any way you like. It works out whether to chat, search the web, '
        "draw or speak.</p>"
    )


def pad_head(intent: str, description: str) -> str:
    name, kannada = MODES[intent]
    return (
        f'<div class="pad-head"><span class="pad-name">{_e(name)}</span>'
        f'<span class="pad-kn" lang="kn">{_e(kannada)}</span></div>'
        f'<p class="pad-desc">{_e(description)}</p>'
    )


def hint() -> str:
    return '<p class="hint">Type in English, Kannada, Hindi, Tamil or Telugu. Typos and follow-ups are fine.</p>'


def header(intent: str, language: str = "English", interpreted: str = "", note: str = "") -> str:
    """Margin marker, mode tab and optional notes shown above a reply."""
    if intent not in MODES:
        intent = "chat"
    name, kannada = MODES[intent]
    lang = ""
    if language and language.strip().lower() != "english":
        lang = f'<span class="lang">{_e(language)}</span>'
    out = (
        f'<span class="mk mk-{intent}"></span>'
        f'<div class="tab t-{intent}"><b>{_e(name)}</b><span lang="kn">{_e(kannada)}</span>{lang}</div>'
    )
    if interpreted:
        out += f'<p class="read-as">Read as: {_e(interpreted)}</p>'
    if note:
        out += f'<p class="read-as">{_e(note)}</p>'
    return out


def strip(intent: str, stages: list, provider: str = "") -> str:
    """The colour control strip: lit ink for the mode used, then the time each step took."""
    if intent not in MODES:
        intent = "chat"
    inks = "".join(f'<i class="ink {k}{" on" if k == intent else ""}"></i>' for k in INK_ORDER)
    parts = "".join(
        f'<span class="stage">{_e(label)} <b>{float(sec):.1f}s</b></span>' for label, sec in stages
    )
    if provider:
        parts += f'<span class="stage">via <b>{_e(provider)}</b></span>'
    return (
        f'<div class="strip" role="img" aria-label="Handled as {_e(MODES[intent][0])}">'
        f'<span class="inks" aria-hidden="true">{inks}</span>{parts}</div>'
    )


def sources(items: list) -> str:
    """Source links as chips. Only http and https links are shown."""
    chips = []
    for n, s in enumerate(items or [], 1):
        url = str(s.get("url", ""))
        parsed = urlparse(url)
        if parsed.scheme not in ("http", "https") or not parsed.netloc:
            continue
        label = parsed.netloc.removeprefix("www.")
        chips.append(
            f'<a href="{_e(url)}" target="_blank" rel="noopener noreferrer" title="{_e(s.get("title", ""))}">'
            f"<b>{n}</b>{_e(label)}</a>"
        )
    return f'<div class="srcs">{"".join(chips)}</div>' if chips else ""


def legend() -> str:
    rows = "".join(
        f'<i class="ink {i} on" aria-hidden="true"></i><span>{_e(MODES[i][0])}'
        f' <span lang="kn">{_e(MODES[i][1])}</span></span>'
        for i in ("chat", "search", "image", "speech")
    )
    return (
        '<p style="font-size:0.85rem;margin:0.8rem 0 0">The strip under each reply lights the ink '
        f'for the mode used and shows how long each step took.</p><div class="legend">{rows}</div>'
    )