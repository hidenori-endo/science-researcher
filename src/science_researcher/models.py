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


class RecordType(StrEnum):
    KNOWN_RESULT = "known_result"
    DERIVED_RESULT = "derived_result"
    COMPUTATIONAL_OBSERVATION = "computational_observation"
    HYPOTHESIS = "hypothesis"
    CONJECTURE = "conjecture"
    COUNTEREXAMPLE = "counterexample"
    OBSTRUCTION = "obstruction"
    FAILED_APPROACH = "failed_approach"
    LEAN_VERIFIED = "lean_verified"
    EXPERIMENTAL_RESULT = "experimental_result"
    METHODOLOGICAL_LESSON = "methodological_lesson"


class EvidenceType(StrEnum):
    COMPUTATIONAL_OBSERVATION = "computational_observation"
    LITERATURE_RESULT = "literature_result"
    THEOREM = "theorem"
    COUNTEREXAMPLE = "counterexample"
    LEAN_PROOF = "lean_proof"
    SYMBOLIC_CALCULATION = "symbolic_calculation"
    DATASET_OBSERVATION = "dataset_observation"
    EXPERIMENTAL_RESULT = "experimental_result"


class EpistemicStatus(StrEnum):
    ESTABLISHED = "established"
    LEAN_VERIFIED = "lean_verified"
    MATHEMATICALLY_DERIVED = "mathematically_derived"
    COMPUTATIONAL = "computational"
    EXPERIMENTAL = "experimental"
    CONJECTURAL = "conjectural"
    SPECULATIVE = "speculative"
    FALSIFIED = "falsified"
    UNKNOWN = "unknown"


class ResearchRelationType(StrEnum):
    SUPPORTS = "SUPPORTS"
    CONTRADICTS = "CONTRADICTS"
    WEAKENS = "WEAKENS"
    REFINES = "REFINES"
    MOTIVATES = "MOTIVATES"
    FALSIFIES = "FALSIFIES"
    DEPENDS_ON = "DEPENDS_ON"
    DERIVED_FROM = "DERIVED_FROM"


RESEARCH_AXES = ("semantic", "domain", "mechanism", "math_structure", "problem_shape", "failure")


@dataclass(slots=True)
class ResearchClaim:
    id: str
    title: str
    statement: str
    record_type: str
    epistemic_status: str
    domain: str
    external_id: str | None = None
    source: str = ""
    axis_texts: dict[str, str] = field(default_factory=dict)
    metadata: dict[str, Any] = field(default_factory=dict)
    created_at: str | None = None

    def axis_text(self, axis: str) -> str:
        if axis not in RESEARCH_AXES:
            raise ValueError(f"unknown axis: {axis}")
        if axis in self.axis_texts:
            return self.axis_texts[axis]
        defaults = {
            "semantic": f"{self.title}. {self.statement}",
            "domain": self.domain,
            "mechanism": "",
            "math_structure": "",
            "problem_shape": "",
            "failure": "",
        }
        return defaults[axis]

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass(slots=True)
class Evidence:
    id: str
    title: str
    summary: str
    evidence_type: str
    epistemic_status: str
    external_id: str | None = None
    source_uri: str = ""
    citation: str = ""
    axis_texts: dict[str, str] = field(default_factory=dict)
    metadata: dict[str, Any] = field(default_factory=dict)
    created_at: str | None = None

    def axis_text(self, axis: str) -> str:
        if axis not in RESEARCH_AXES:
            raise ValueError(f"unknown axis: {axis}")
        if axis in self.axis_texts:
            return self.axis_texts[axis]
        defaults = {
            "semantic": f"{self.title}. {self.summary}",
            "domain": str(self.metadata.get("domain", "")),
            "mechanism": "",
            "math_structure": "",
            "problem_shape": "",
            "failure": "",
        }
        return defaults[axis]

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


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
