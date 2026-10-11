import math
import re
from collections import Counter

STOP = set("a an and are as at be by can do does for from has how in is it its of on or that the their this to was what when which who with".split())


def tokens(text: str) -> list[str]:
    out = []
    for t in re.findall(r"[a-z0-9]+", text.lower()):
        if t in STOP:
            continue
        if len(t) > 5:
            t = re.sub(r"(ing|ed|es)$", "", t)
        if len(t) > 3 and t.endswith("s") and not t.endswith("ss"):
            t = t[:-1]
        out.append(t)
    return out


def document(p: dict) -> str:
    """Fields worth matching; the title counts twice."""
    parts = [p["title"], p["title"], p["label"], p.get("abstract", ""), p.get("vector", ""), p.get("effect", ""),
             p.get("mechanism", ""), p.get("tested_against", ""), p.get("may_apply", "")]
    return " ".join(x for x in parts if x)


class KeywordIndex:
    """Okapi BM25 over title, abstract, and table fields. 68 papers do not need embeddings."""

    def __init__(self, papers: list[dict], k1: float = 1.4, b: float = 0.7):
        self.k1, self.b = k1, b
        self.docs = [Counter(tokens(document(p))) for p in papers]
        self.lengths = [sum(d.values()) for d in self.docs]
        self.avg = sum(self.lengths) / len(self.lengths)
        df = Counter(t for d in self.docs for t in d)
        n = len(self.docs)
        self.idf = {t: math.log(1 + (n - c + 0.5) / (c + 0.5)) for t, c in df.items()}
        self.phrases = [" ".join(tokens(document(p))) for p in papers]

    def score(self, query: str) -> list[float]:
        q = tokens(query)
        scores = []
        for d, length in zip(self.docs, self.lengths, strict=True):
            norm = self.k1 * (1 - self.b + self.b * length / self.avg)
            scores.append(sum(self.idf.get(t, 0) * d[t] * (self.k1 + 1) / (d[t] + norm) for t in set(q) if t in d))
        joined = " ".join(tokens(query))
        if len(joined.split()) > 1:  # an exact multi-word phrase such as "label flip" counts double
            scores = [s * 2 if joined in text else s for s, text in zip(scores, self.phrases, strict=True)]
        return scores

    def search(self, query: str) -> list[tuple[int, float]]:
        """Best-first (index, score) of papers that share at least one query word."""
        ranked = sorted(enumerate(self.score(query)), key=lambda x: -x[1])
        return [(i, s) for i, s in ranked if s > 0]
