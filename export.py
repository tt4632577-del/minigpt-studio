"""Turn the conversation into a Markdown file the user can download."""


def chat_to_markdown(messages: list[dict], title: str = "MiniGPT Studio chat") -> str:
    lines = [f"# {title}", ""]
    for m in messages:
        if m["role"] == "user":
            lines += [f"**You:** {m['content']}", ""]
            continue
        mode = m.get("intent", "chat")
        if m["kind"] == "image":
            body = f"[image] {m['content']}"
        elif m["kind"] == "speech":
            body = f"[spoken] {m['content']}"
        else:
            body = m["content"]
        lines += [f"**Assistant ({mode}):** {body}", ""]
        found = m.get("sources") or []
        for i, s in enumerate(found, 1):
            lines.append(f"- [{i}] {s.get('title', '')} {s.get('url', '')}".rstrip())
        if found:
            lines.append("")
    return "\n".join(lines)