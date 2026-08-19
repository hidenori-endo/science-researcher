from __future__ import annotations

import uuid
from dataclasses import dataclass
from typing import Any

from .embeddings import cosine_similarity, overlap_ratio
from .models import (
    RESEARCH_AXES,
    EpistemicStatus,
    Evidence,
    EvidenceType,
    RecordType,
    ResearchClaim,
    ResearchRelationType,
)


@dataclass(slots=True)
class BundleRelation:
    claim_external_id: str
    relation: str
    evidence_external_id: str | None = None
    target_claim_external_id: str | None = None
    metadata: dict[str, Any] | None = None


@dataclass(slots=True)
class ResearchBundle:
    schema_version: int
    claims: list[ResearchClaim]
    evidence: list[Evidence]
    relations: list[BundleRelation]


def _validate_axis_texts(value: Any, *, field_name: str) -> dict[str, str]:
    if value is None:
        return {}
    if not isinstance(value, dict):
        raise TypeError(f"{field_name} must be an object")
    invalid = set(value) - set(RESEARCH_AXES)
    if invalid:
        raise ValueError(f"{field_name} contains unknown axes: {sorted(invalid)}")
    if any(not isinstance(text, str) for text in value.values()):
        raise ValueError(f"{field_name} values must be strings")
    return dict(value)


def _validate_metadata(value: Any, *, field_name: str = "metadata") -> dict[str, Any]:
    if value is None:
        return {}
    if not isinstance(value, dict):
        raise TypeError(f"{field_name} must be an object")
    return dict(value)


def validate_claim(claim: ResearchClaim) -> ResearchClaim:
    try:
        RecordType(claim.record_type)
    except ValueError as exc:
        raise ValueError(f"invalid record_type: {claim.record_type}") from exc
    try:
        EpistemicStatus(claim.epistemic_status)
    except ValueError as exc:
        raise ValueError(f"invalid epistemic_status: {claim.epistemic_status}") from exc
    if not claim.title.strip():
        raise ValueError("claim title must not be empty")
    if not claim.statement.strip():
        raise ValueError("claim statement must not be empty")
    if not claim.domain.strip():
        raise ValueError("claim domain must not be empty")
    _validate_axis_texts(claim.axis_texts, field_name="claim.axis_texts")
    _validate_metadata(claim.metadata)
    return claim


def validate_evidence(evidence: Evidence) -> Evidence:
    try:
        EvidenceType(evidence.evidence_type)
    except ValueError as exc:
        raise ValueError(f"invalid evidence_type: {evidence.evidence_type}") from exc
    try:
        EpistemicStatus(evidence.epistemic_status)
    except ValueError as exc:
        raise ValueError(f"invalid epistemic_status: {evidence.epistemic_status}") from exc
    if not evidence.title.strip():
        raise ValueError("evidence title must not be empty")
    if not evidence.summary.strip():
        raise ValueError("evidence summary must not be empty")
    _validate_axis_texts(evidence.axis_texts, field_name="evidence.axis_texts")
    _validate_metadata(evidence.metadata)
    return evidence


def validate_relation_type(relation: str) -> str:
    try:
        return ResearchRelationType(relation).value
    except ValueError as exc:
        raise ValueError(f"invalid research relation: {relation}") from exc


def validate_research_bundle(data: dict[str, Any]) -> ResearchBundle:
    if not isinstance(data, dict):
        raise TypeError("research bundle must be an object")
    schema_version = data.get("schema_version")
    if schema_version != 1:
        raise ValueError(f"unsupported research bundle schema_version: {schema_version!r}")

    raw_claims = data.get("claims", [])
    raw_evidence = data.get("evidence", [])
    raw_relations = data.get("relations", [])
    if not isinstance(raw_claims, list) or not isinstance(raw_evidence, list) or not isinstance(raw_relations, list):
        raise TypeError("claims, evidence, and relations must be arrays")

    claims: list[ResearchClaim] = []
    claim_external_ids: set[str] = set()
    for index, item in enumerate(raw_claims):
        if not isinstance(item, dict):
            raise TypeError(f"claims[{index}] must be an object")
        external_id = item.get("external_id")
        if not isinstance(external_id, str) or not external_id.strip():
            raise ValueError(f"claims[{index}].external_id is required for idempotent import")
        if external_id in claim_external_ids:
            raise ValueError(f"duplicate claim external_id: {external_id}")
        claim_external_ids.add(external_id)
        claim = ResearchClaim(
            id=str(uuid.uuid4()),
            external_id=external_id,
            title=str(item.get("title", "")),
            statement=str(item.get("statement", "")),
            record_type=str(item.get("record_type", "")),
            epistemic_status=str(item.get("epistemic_status", "")),
            domain=str(item.get("domain", "")),
            source=str(item.get("source", "")),
            axis_texts=_validate_axis_texts(item.get("axis_texts"), field_name=f"claims[{index}].axis_texts"),
            metadata=_validate_metadata(item.get("metadata"), field_name=f"claims[{index}].metadata"),
        )
        claims.append(validate_claim(claim))

    evidence: list[Evidence] = []
    evidence_external_ids: set[str] = set()
    for index, item in enumerate(raw_evidence):
        if not isinstance(item, dict):
            raise TypeError(f"evidence[{index}] must be an object")
        external_id = item.get("external_id")
        if not isinstance(external_id, str) or not external_id.strip():
            raise ValueError(f"evidence[{index}].external_id is required for idempotent import")
        if external_id in evidence_external_ids:
            raise ValueError(f"duplicate evidence external_id: {external_id}")
        evidence_external_ids.add(external_id)
        record = Evidence(
            id=str(uuid.uuid4()),
            external_id=external_id,
            title=str(item.get("title", "")),
            summary=str(item.get("summary", "")),
            evidence_type=str(item.get("evidence_type", "")),
            epistemic_status=str(item.get("epistemic_status", "")),
            source_uri=str(item.get("source_uri", "")),
            citation=str(item.get("citation", "")),
            axis_texts=_validate_axis_texts(item.get("axis_texts"), field_name=f"evidence[{index}].axis_texts"),
            metadata=_validate_metadata(item.get("metadata"), field_name=f"evidence[{index}].metadata"),
        )
        evidence.append(validate_evidence(record))

    relations: list[BundleRelation] = []
    for index, item in enumerate(raw_relations):
        if not isinstance(item, dict):
            raise TypeError(f"relations[{index}] must be an object")
        claim_external_id = item.get("claim")
        evidence_external_id = item.get("evidence")
        target_claim_external_id = item.get("target_claim")
        if not isinstance(claim_external_id, str) or claim_external_id not in claim_external_ids:
            raise ValueError(f"relations[{index}].claim must reference a claim in the bundle")
        has_evidence = isinstance(evidence_external_id, str)
        has_target_claim = isinstance(target_claim_external_id, str)
        if has_evidence == has_target_claim:
            raise ValueError(f"relations[{index}] must reference exactly one of evidence or target_claim")
        if has_evidence and evidence_external_id not in evidence_external_ids:
            raise ValueError(f"relations[{index}].evidence must reference evidence in the bundle")
        if has_target_claim and target_claim_external_id not in claim_external_ids:
            raise ValueError(f"relations[{index}].target_claim must reference a claim in the bundle")
        relations.append(
            BundleRelation(
                claim_external_id=claim_external_id,
                evidence_external_id=evidence_external_id if has_evidence else None,
                target_claim_external_id=target_claim_external_id if has_target_claim else None,
                relation=validate_relation_type(str(item.get("relation", ""))),
                metadata=_validate_metadata(item.get("metadata"), field_name=f"relations[{index}].metadata"),
            )
        )

    return ResearchBundle(
        schema_version=schema_version,
        claims=claims,
        evidence=evidence,
        relations=relations,
    )


class ResearchIndex:
    """Axis-aware indexing for first-class research claims and evidence."""

    def __init__(self, store: object, embedder: object) -> None:
        self.store = store
        self.embedder = embedder

    def index_claim(self, claim: ResearchClaim) -> None:
        validate_claim(claim)
        self.store.upsert_research_claim(claim)
        self._index("claim", claim.id, claim)

    def index_evidence(self, evidence: Evidence) -> None:
        validate_evidence(evidence)
        self.store.upsert_evidence(evidence)
        self._index("evidence", evidence.id, evidence)

    def index_existing_claim(self, claim: ResearchClaim) -> None:
        self._index("claim", claim.id, claim)

    def index_existing_evidence(self, evidence: Evidence) -> None:
        self._index("evidence", evidence.id, evidence)

    def _index(self, entity_kind: str, entity_id: str, record: ResearchClaim | Evidence) -> None:
        for axis in RESEARCH_AXES:
            canonical_text = record.axis_text(axis)
            self.store.put_research_vector(
                entity_kind,
                entity_id,
                axis,
                self.embedder.embed(canonical_text),
                canonical_text=canonical_text,
            )

    def search(
        self,
        query: ResearchClaim | Evidence,
        *,
        entity_kind: str | None = None,
        limit: int = 10,
        mode: str = "analogy",
    ) -> list[dict[str, Any]]:
        if entity_kind not in (None, "claim", "evidence"):
            raise ValueError("entity_kind must be claim, evidence, or None")
        if mode not in ("analogy", "memory"):
            raise ValueError("mode must be analogy or memory")
        query_vectors = {axis: self.embedder.embed(query.axis_text(axis)) for axis in RESEARCH_AXES}
        records: list[tuple[str, ResearchClaim | Evidence]] = []
        if entity_kind in (None, "claim"):
            records.extend(("claim", item) for item in self.store.list_research_claims())
        if entity_kind in (None, "evidence"):
            records.extend(("evidence", item) for item in self.store.list_evidence())

        hits: list[dict[str, Any]] = []
        for kind, record in records:
            try:
                stored_vectors = {
                    axis: self.store.get_research_vector(kind, record.id, axis)
                    for axis in RESEARCH_AXES
                }
            except KeyError:
                # Records created through the low-level store API can exist before
                # indexing. Search only returns records with a complete axis index.
                continue
            similarities = {
                axis: cosine_similarity(query_vectors[axis], stored_vectors[axis])
                for axis in RESEARCH_AXES
            }
            domain_similarity = min(1.0, max(0.0, similarities["domain"]))
            domain_distance = 1.0 - domain_similarity
            failure_overlap = overlap_ratio(query.axis_text("failure"), record.axis_text("failure"))
            if mode == "analogy":
                score = (
                    0.50 * similarities["mechanism"]
                    + 0.20 * similarities["math_structure"]
                    + 0.15 * similarities["problem_shape"]
                    + 0.15 * similarities["semantic"]
                    + 0.20 * domain_distance
                    - 0.20 * failure_overlap
                )
            else:
                # Memory lookup should surface same-domain prior work and matching
                # failure modes rather than reward distance as analogy search does.
                score = (
                    0.30 * similarities["mechanism"]
                    + 0.15 * similarities["math_structure"]
                    + 0.15 * similarities["problem_shape"]
                    + 0.20 * similarities["semantic"]
                    + 0.10 * domain_similarity
                    + 0.10 * failure_overlap
                )
            source_type = record.record_type if kind == "claim" else record.evidence_type
            domain = record.domain if kind == "claim" else str(record.metadata.get("domain", "unknown"))
            hits.append(
                {
                    "entity_kind": kind,
                    "id": record.id,
                    "external_id": record.external_id,
                    "title": record.title,
                    "domain": domain,
                    "epistemic_status": record.epistemic_status,
                    "source_type": source_type,
                    "score": score,
                    "mechanism_similarity": similarities["mechanism"],
                    "structure_similarity": similarities["math_structure"],
                    "problem_shape_similarity": similarities["problem_shape"],
                    "semantic_similarity": similarities["semantic"],
                    "domain_distance": domain_distance,
                    "failure_overlap": failure_overlap,
                }
            )
        hits.sort(key=lambda item: item["score"], reverse=True)
        return hits[:limit]
