"""Thumbs up/down log and simple statistics (saved in feedback.csv next to the app)."""
import csv
import os
import time
from collections import defaultdict

FILE = os.path.join(os.path.dirname(os.path.abspath(__file__)), "feedback.csv")
FIELDS = ["time", "mode", "intent", "provider", "seconds", "rating"]


def log(mode: str, intent: str, provider: str, seconds: float, rating: str) -> None:
    new = not os.path.exists(FILE)
    with open(FILE, "a", newline="", encoding="utf-8") as f:
        w = csv.writer(f)
        if new:
            w.writerow(FIELDS)
        w.writerow([time.strftime("%Y-%m-%d %H:%M:%S"), mode, intent, provider, f"{seconds:.2f}", rating])


def stats() -> dict:
    """Totals, thumbs-up share and average answer time per provider."""
    out = {"total": 0, "up": 0, "down": 0, "by_provider": {}}
    if not os.path.exists(FILE):
        return out
    times = defaultdict(list)
    with open(FILE, newline="", encoding="utf-8") as f:
        for row in csv.DictReader(f):
            out["total"] += 1
            out["up" if row.get("rating") == "up" else "down"] += 1
            try:
                times[row.get("provider") or "-"].append(float(row["seconds"]))
            except (ValueError, KeyError):
                pass
    out["by_provider"] = {p: sum(v) / len(v) for p, v in times.items()}
    return out