"""Ask questions about your own document (PDF, TXT or MD).

Pure Python, no embeddings: the document is cut into passages and the best matches for a question
are found with BM25 keyword scoring. The matching passages are then given to the language model as sources.
"""
import io
import math
import re
from collections import Counter

MAX_PAGES = 500
STOP = set(
    "a an and are as at be by for from has have he in is it its of on or that the to was were will with "
    "this these those you your i we they not but if then than so do does did can could should would about "
    "into over after before what which who whom when where why how me my our their there here also".split()
)
WORD = re.compile(r"[\wऀ-෿]+")  # letters and digits, plus Indic scripts with their vowel signs


def tokens(text: str) -> list[str]:
    return [w for w in WORD.findall(text.lower()) if w not in STOP and len(w) > 1]


def extract_text(name: str, data: bytes) -> list[tuple[str, str]]:
    """Return [(page label, text)]. PDFs give one entry per page; text files give one entry."""
    if name.lower().endswith(".pdf"):
        from pypdf import PdfReader

        reader = PdfReader(io.BytesIO(data))
        return [(f"p.{i}", page.extract_text() or "") for i, page in enumerate(reader.pages[:MAX_PAGES], 1)]
    return [("text", data.decode("utf-8", errors="replace"))]


def chunk_pages(pages: list[tuple[str, str]], size: int = 900, overlap: int = 150) -> list[dict]:
    """Cut pages into overlapping passages of about `size` characters."""
    chunks = []
    for label, text in pages:
        text = re.sub(r"\s+", " ", text).strip()
        start = 0
        while text and start < len(text):
            end = min(start + size, len(text))
            if end < len(text):
                cut = text.rfind(". ", start + size // 2, end)
                if cut != -1:
                    end = cut + 1
            piece = text[start:end].strip()
            if piece:
                chunks.append({"label": label, "text": piece})
            if end >= len(text):
                break
            start = max(end - overlap, start + 1)
    return chunks


class DocIndex:
    """BM25 search over passages."""

    def __init__(self, chunks: list[dict]):
        self.chunks = chunks
        self.tf = [Counter(tokens(c["text"])) for c in chunks]
        self.len = [sum(tf.values()) for tf in self.tf]
        self.n = len(chunks)
        self.avg = (sum(self.len) / self.n) if self.n else 0.0
        self.df: Counter = Counter()
        for tf in self.tf:
            self.df.update(tf.keys())

    def search(self, query: str, k: int = 4) -> list[dict]:
        words = tokens(query)
        if not words or not self.n:
            return []
        scored = []
        for i, tf in enumerate(self.tf):
            score = 0.0
            for w in words:
                f = tf.get(w, 0)
                if not f:
                    continue
                df = self.df[w]
                idf = math.log(1 + (self.n - df + 0.5) / (df + 0.5))
                norm = f + 1.5 * (0.25 + 0.75 * self.len[i] / (self.avg or 1))
                score += idf * f * 2.5 / norm
            if score > 0:
                scored.append((score, i))
        scored.sort(reverse=True)
        return [self.chunks[i] for _, i in scored[:k]]


def as_sources(name: str, hits: list[dict]) -> list[dict]:
    """Shape the matching passages like web results so the rest of the app can reuse them."""
    return [{"title": f"{name} {h['label']}", "url": "", "snippet": h["text"][:900]} for h in hits]


def overview(chunks: list[dict], max_chars: int = 7000) -> list[dict]:
    """Pick passages spread evenly across the whole document, for summaries and quizzes."""
    if not chunks:
        return []
    per = max(1, max_chars // 900)
    if len(chunks) <= per:
        return list(chunks)
    step = len(chunks) / per
    return [chunks[int(i * step)] for i in range(per)]