from integritymap.data import load_bundle
from integritymap.search import KeywordIndex, tokens

PAPERS = load_bundle().papers
INDEX = KeywordIndex(PAPERS)


def top(query: str, k: int = 5) -> list[str]:
    return [PAPERS[i]["key"] for i, _ in INDEX.search(query)[:k]]


def test_tokens_drop_stopwords_and_suffixes():
    assert tokens("The flips of labels") == ["flip", "label"]


def test_known_papers_rank_high():
    assert "ghitu2026certification" in top("certificate poisoned points")
    assert "ding2026rubrics" in top("rubric")
    assert "rando2024universal" in top("universal jailbreak backdoor")


def test_unrelated_query_returns_nothing():
    assert INDEX.search("zebra xylophone") == []
