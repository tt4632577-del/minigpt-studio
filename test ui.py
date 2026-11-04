import pytest

import ui


def test_header_escapes_user_text():
    out = ui.header("search", "English", interpreted='<script>alert("x")</script>')
    assert "<script>" not in out
    assert "&lt;script&gt;" in out


def test_header_uses_mode_names():
    out = ui.header("image", "Kannada")
    assert "Draw" in out and "mk-image" in out and "Kannada" in out


def test_unknown_intent_falls_back_to_chat():
    assert "mk-chat" in ui.header("nonsense")


def test_strip_lights_only_the_active_ink():
    out = ui.strip("image", [("Understood", 0.8), ("Drew", 6.25)], "groq")
    assert out.count("ink image on") == 1
    assert out.count(" on") == 1
    assert "0.8s" in out and ("6.2s" in out or "6.3s" in out)
    assert "via <b>groq</b>" in out


def test_sources_only_allow_web_links():
    items = [
        {"title": "Good", "url": "https://www.presidencyuniversity.in/page"},
        {"title": "Bad", "url": "javascript:alert(1)"},
        {"title": "Odd", "url": "not a url"},
    ]
    out = ui.sources(items)
    assert "</b>presidencyuniversity.in</a>" in out  # label drops the www.
    assert "javascript" not in out and "not a url" not in out


def test_sources_empty_gives_nothing():
    assert ui.sources([]) == ""


def test_every_pad_has_a_mode():
    for intent, description, example in ui.PADS:
        assert intent in ui.MODES and description and example


def test_unknown_theme_uses_the_first_theme():
    assert ui.css("no such theme") == ui.css(ui.THEME_NAMES[0])


@pytest.mark.parametrize("name", ui.THEME_NAMES)
def test_theme_text_is_readable(name):
    t = ui.THEMES[name]
    assert ui.contrast(t["ink"], t["bg"]) >= 7
    assert ui.contrast(t["ink"], t["card"]) >= 7
    assert ui.contrast(t["ink"], t["card2"]) >= 7
    assert ui.contrast(ui.muted(t), t["bg"]) >= 4.5
    assert ui.contrast(ui.muted(t), t["card"]) >= 4.5


@pytest.mark.parametrize("name", ui.THEME_NAMES)
def test_mode_colours_work_on_page_and_with_their_labels(name):
    t = ui.THEMES[name]
    for intent in ui.MODES:
        assert ui.contrast(t[intent], t["bg"]) >= 4.5, intent  # rules, fills and links stand out
        assert ui.contrast(ui.on_color(t[intent]), t[intent]) >= 4.5, intent  # tab text is readable


@pytest.mark.parametrize("name", ui.THEME_NAMES)
def test_css_defines_every_variable(name):
    out = ui.css(name)
    for var in ("--bg", "--card", "--ink", "--muted", "--line", "--c-chat", "--on-search", "--c-image", "--c-speech"):
        assert var + ":" in out