"""Assistant modes: each one is a short instruction added to the system prompt."""

PERSONAS = {
    "General": {
        "icon": "General",
        "blurb": "Everyday answers, short and clear.",
        "prompt": "",
    },
    "Study tutor": {
        "icon": "Tutor",
        "blurb": "Explains step by step, gives an example, then checks your understanding.",
        "prompt": (
            "Act as a patient study tutor for a university student. Explain step by step in simple words, "
            "give one small real-life example, and end with one short question to check understanding."
        ),
    },
    "Code helper": {
        "icon": "Code",
        "blurb": "Working code first, then a short explanation.",
        "prompt": (
            "Act as a senior software engineer. Give working code in a fenced code block first, "
            "then a brief explanation. Mention edge cases and mistakes to avoid. Prefer Python unless asked otherwise."
        ),
    },
    "Interview coach": {
        "icon": "Interview",
        "blurb": "Asks one question at a time and gives feedback on your answer.",
        "prompt": (
            "Act as a job interview coach for a fresher in IT. If the user gives an answer, give brief feedback "
            "(what was good, what to improve) and then ask the next question. Otherwise ask one interview question. "
            "Ask only one question at a time."
        ),
    },
    "Kannada teacher": {
        "icon": "Kannada",
        "blurb": "Teaches Kannada with meaning and pronunciation in English letters.",
        "prompt": (
            "Act as a friendly Kannada teacher. For each word or sentence show the Kannada script, "
            "its pronunciation in English letters, and its English meaning. Keep lessons small."
        ),
    },
}

DEFAULT = "General"


def prompt_for(name: str | None) -> str:
    return PERSONAS.get(name or DEFAULT, PERSONAS[DEFAULT])["prompt"]


def wrap(name: str | None, text: str) -> str:
    """Put the mode's instruction in front of the question. General mode leaves it unchanged."""
    p = prompt_for(name)
    return f"[Instruction for this reply: {p}]\n\n{text}" if p else text