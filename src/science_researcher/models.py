from __future__ import annotations

from dataclasses import asdict, dataclass, field
from enum import StrEnum
from typing import Any


class NodeKind(StrEnum):
    BREAKTHROUGH = "breakthrough"
    PROBLEM = "problem"
    CONCEPT = "concept"
    THEOREM = "theorem"
    FAILURE = "failure"


class ObligationStatus(StrEnum):
    KNOWN = "known"
    PROVED = "proved"
    COMPUTATIONAL = "computational"
    CONJECTURAL = "conjectural"
    FALSE = "false"
    UNKNOWN = "unknown"


@dataclass(slots=True)
class ScientificNode:
    id: str
    kind: str
    title: str
    domain: str
    summary: str
    mechanism: str
    math_structure: str
    problem_shape: str
    failure_modes: str = ""
    metadata: dict[str, Any] = field(default_factory=dict)

    def axis_text(self, axis: str) -> str:
        mapping = {
            "semantic": f"{self.title}. {self.summary}",
            "domain": self.domain,
            "mechanism": self.mechanism,
            "math_structure": self.math_structure,
            "problem_shape": self.problem_shape,
            "failure": self.failure_modes,
        }
        try:
            return mapping[axis]
        except KeyError as exc:
            raise ValueError(f"unknown axis: {axis}") from exc

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass(slots=True)
class Reframing:
    label: str
    text: str
    mechanism_query: str
    structure_query: str
    problem_shape_query: str
    forbidden_shortcuts: list[str] = field(default_factory=list)


@dataclass(slots=True)
class AnalogyCandidate:
    node_id: str
    title: str
    domain: str
    score: float
    mechanism_similarity: float
    structure_similarity: float
    problem_shape_similarity: float
    semantic_similarity: float
    domain_distance: float
    failure_overlap: float


@dataclass(slots=True)
class HypothesisDraft:
    title: str
    bridge: str
    prediction: str
    rationale: str
    source_node_id: str


@dataclass(slots=True)
class Critique:
    score: float
    verdict: str
    failure_reason: str
    checks: list[str]


@dataclass(slots=True)
class ProofObligation:
    statement: str
    status: str = ObligationStatus.UNKNOWN
    verification_method: str = "literature-or-proof"
    notes: str = ""
