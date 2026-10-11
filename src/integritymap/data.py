import json
import os
from dataclasses import dataclass
from pathlib import Path

DATA_DIR = Path(os.environ.get("INTEGRITYMAP_DATA", Path(__file__).resolve().parents[2] / "data"))


@dataclass(frozen=True)
class Stage:
    id: str
    name: str
    role: str
    attacker: str
    lost: str


# The four stages of Section 2.1; the attacker and evidence lines follow Sections 2.2 and 2.3.
STAGES = [
    Stage("source", "Annotation source",
          "A human annotator or a language-model judge decides which of two responses is better.",
          "A1, annotation access: the attacker produces corrupted judgments or controls the inputs a judge rates.",
          "Who produced each label. Only 3 of the 14 audited datasets keep a per-label annotator ID."),
    Stage("dataset", "Preference dataset",
          "Each decision is stored as a prompt, a chosen response, and a rejected response.",
          "A2, dataset access: the attacker flips labels or inserts records.",
          "The single pairs. A trained reward model keeps no inspectable copy of them."),
    Stage("channel", "Reward or verification channel",
          "A reward model, a verifier, or a rubric turns stored judgments into training scores.",
          "A3, channel access: the attacker controls a reward model, a verifier, or the rubric it applies.",
          "Which scores caused which policy updates."),
    Stage("model", "Trained policy",
          "The optimizer (RLHF, DPO, RLVR) updates the policy with these scores.",
          "Out of scope: the survey studies corrupted supervision, not attacks on the optimizer.",
          "Only behavior is visible, not the records that caused it."),
]
STAGE_BY_ID = {s.id: s for s in STAGES}
ATTACK_STAGES = [s.id for s in STAGES[:3]]

# Rows of Table 2: (id, name, stage it acts on).
INTERVENTIONS = [
    ("provenance", "Source and provenance", "source"),
    ("annotation_checks", "Annotation checks", "source"),
    ("dataset_filtering", "Dataset filtering", "dataset"),
    ("robust_objectives", "Robust objectives", "dataset"),
    ("channel_validation", "Channel validation", "channel"),
    ("forensics", "Post-training forensics", "model"),
]
INTERVENTION_NAME = {i: n for i, n, _ in INTERVENTIONS}


@dataclass(frozen=True)
class Bundle:
    papers: list[dict]
    evaluations: list[dict]
    noise_only: dict[str, list[str]]
    budgets: list[dict]
    provenance: list[dict]


def load_bundle(data_dir: Path = DATA_DIR) -> Bundle:
    read = lambda name: json.loads((data_dir / name).read_text())
    coverage = read("coverage.json")
    return Bundle(
        papers=read("papers.json"),
        evaluations=coverage["evaluations"],
        noise_only=coverage["noise_only"],
        budgets=read("budgets.json"),
        provenance=read("provenance.json"),
    )
