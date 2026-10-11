from collections import Counter

from integritymap.data import load_bundle

B = load_bundle()


def test_corpus_counts_match_the_paper():
    roles = Counter(p["role"] for p in B.papers)
    assert roles == {"attack": 28, "defense": 40}
    assert Counter(p["stage"] for p in B.papers if p["role"] == "attack") == {"source": 13, "dataset": 12, "channel": 3}
    assert sum(p.get("defense_tested", False) for p in B.papers) == 17
    assert Counter(p["scope"] for p in B.papers if p["role"] == "defense") == {"attack": 14, "noise": 24, "theory": 2}


def test_coverage_matches_table_6():
    out = Counter(e["outcome"] for e in B.evaluations)
    assert len(B.evaluations) == 73 and out == {"works": 13, "partial": 19, "fails": 40, "unclear": 1}
    cells = Counter((e["row"], e["column"]) for e in B.evaluations)
    assert cells[("annotation_checks", "source")] == 27
    assert cells[("dataset_filtering", "dataset")] == 14
    assert not any(e["column"] == "channel" and e["outcome"] == "works" for e in B.evaluations)
    assert {k: len(v) for k, v in B.noise_only.items()} == {"annotation_checks": 2, "dataset_filtering": 6, "robust_objectives": 8, "channel_validation": 8}


def test_every_record_points_to_a_paper():
    keys = {p["key"] for p in B.papers}
    assert all(e["paper"] in keys for e in B.evaluations)
    assert all(b["key"] in keys for b in B.budgets)
    assert len(B.budgets) == 16 and len(B.provenance) == 14
