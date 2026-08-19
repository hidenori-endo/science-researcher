from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from .models import Evidence, ResearchClaim, ScientificNode
from .research import ResearchIndex
from .retrieval import MultiAxisRetriever


@dataclass(slots=True)
class HybridAnalogyCandidate:
    """A retrieval hit normalized so the discovery loop can mutate it as a ScientificNode."""

    node_id: str
    source_kind: str
    source_id: str
    title: str
    domain: str
    score: float
    mechanism_similarity: float
    structure_similarity: float
    problem_shape_similarity: float
    semantic_similarity: float
    domain_distance: float
    failure_overlap: float
    epistemic_status: str | None = None
    source_type: str | None = None


@dataclass(slots=True)
class HybridRetrievalResult:
    analogies: list[HybridAnalogyCandidate]
    research_memory: list[dict[str, Any]]


def research_record_to_node(entity_kind: str, record: ResearchClaim | Evidence) -> ScientificNode:
    """Project canonical research memory into the legacy ScientificNode interface.

    The projection is deliberately stored with kind ``research_memory`` so it can
    satisfy hypothesis provenance foreign keys without entering the historical
    breakthrough retrieval pool on later runs.
    """

    if entity_kind == "claim":
        assert isinstance(record, ResearchClaim)
        domain = record.domain
        summary = record.statement
        source_type = record.record_type
        provenance = record.source
    elif entity_kind == "evidence":
        assert isinstance(record, Evidence)
        domain = str(record.metadata.get("domain", "unknown"))
        summary = record.summary
        source_type = record.evidence_type
        provenance = record.citation or record.source_uri
    else:
        raise ValueError("entity_kind must be claim or evidence")

    semantic = record.axis_text("semantic")
    mechanism = record.axis_text("mechanism") or semantic
    math_structure = record.axis_text("math_structure") or mechanism
    problem_shape = record.axis_text("problem_shape") or semantic

    return ScientificNode(
        id=f"research-memory:{entity_kind}:{record.id}",
        kind="research_memory",
        title=record.title,
        domain=domain,
        summary=summary,
        mechanism=mechanism,
        math_structure=math_structure,
        problem_shape=problem_shape,
        failure_modes=record.axis_text("failure"),
        metadata={
            "research_memory_kind": entity_kind,
            "research_memory_id": record.id,
            "external_id": record.external_id,
            "epistemic_status": record.epistemic_status,
            "source_type": source_type,
            "provenance": provenance,
        },
    )


class HybridRetriever:
    """Merge historical analogies with reusable first-class research memory.

    Claims can become analogy sources. Evidence is retrieved as context rather than
    being mutated directly into a new hypothesis: an observation is evidence for or
    against a claim, not automatically a transferable scientific mechanism.
    """

    def __init__(
        self,
        store: object,
        node_retriever: MultiAxisRetriever,
        research_index: ResearchIndex,
    ) -> None:
        self.store = store
        self.node_retriever = node_retriever
        self.research_index = research_index
        self.embedder = node_retriever.embedder

    def retrieve(
        self,
        query: ScientificNode,
        *,
        limit: int = 5,
        memory_limit: int | None = None,
    ) -> HybridRetrievalResult:
        pool_limit = max(limit * 3, limit)
        resolved_memory_limit = memory_limit or max(limit * 3, 10)
        node_hits = self.node_retriever.search(query, limit=pool_limit)
        research_query = self._research_query(query)
        claim_hits = self.research_index.search(
            research_query,
            entity_kind="claim",
            limit=pool_limit,
            mode="analogy",
        )
        memory_hits = self.research_index.search(
            research_query,
            limit=resolved_memory_limit,
            mode="memory",
        )

        candidates = [
            HybridAnalogyCandidate(
                node_id=hit.node_id,
                source_kind="node",
                source_id=hit.node_id,
                title=hit.title,
                domain=hit.domain,
                score=hit.score,
                mechanism_similarity=hit.mechanism_similarity,
                structure_similarity=hit.structure_similarity,
                problem_shape_similarity=hit.problem_shape_similarity,
                semantic_similarity=hit.semantic_similarity,
                domain_distance=hit.domain_distance,
                failure_overlap=hit.failure_overlap,
            )
            for hit in node_hits
        ]
        candidates.extend(self._claim_candidate(hit) for hit in claim_hits)
        candidates.sort(key=lambda item: item.score, reverse=True)
        selected = candidates[:limit]

        for candidate in selected:
            if candidate.source_kind == "claim":
                claim = self.store.get_research_claim(candidate.source_id)
                self.store.upsert_node(research_record_to_node("claim", claim))

        return HybridRetrievalResult(analogies=selected, research_memory=memory_hits)

    def search(self, query: ScientificNode, *, limit: int = 5) -> list[HybridAnalogyCandidate]:
        return self.retrieve(query, limit=limit).analogies

    def contextualize(
        self,
        analogy: ScientificNode,
        research_memory: list[dict[str, Any]],
    ) -> ScientificNode:
        """Attach retrieved memory to the provider payload without changing canonical nodes."""

        metadata = dict(analogy.metadata)
        metadata["retrieved_research_memory"] = [
            {
                "entity_kind": hit["entity_kind"],
                "id": hit["id"],
                "external_id": hit["external_id"],
                "title": hit["title"],
                "domain": hit["domain"],
                "epistemic_status": hit["epistemic_status"],
                "source_type": hit["source_type"],
                "score": hit["score"],
            }
            for hit in research_memory
        ]
        return ScientificNode(
            id=analogy.id,
            kind=analogy.kind,
            title=analogy.title,
            domain=analogy.domain,
            summary=analogy.summary,
            mechanism=analogy.mechanism,
            math_structure=analogy.math_structure,
            problem_shape=analogy.problem_shape,
            failure_modes=analogy.failure_modes,
            metadata=metadata,
        )

    def _research_query(self, query: ScientificNode) -> ResearchClaim:
        return ResearchClaim(
            id=f"research-query:{query.id}",
            title=query.title,
            statement=query.summary,
            record_type="hypothesis",
            epistemic_status="unknown",
            domain=query.domain,
            axis_texts={
                "semantic": query.axis_text("semantic"),
                "domain": query.axis_text("domain"),
                "mechanism": query.axis_text("mechanism"),
                "math_structure": query.axis_text("math_structure"),
                "problem_shape": query.axis_text("problem_shape"),
                "failure": query.axis_text("failure"),
            },
        )

    def _claim_candidate(self, hit: dict[str, Any]) -> HybridAnalogyCandidate:
        return HybridAnalogyCandidate(
            node_id=f"research-memory:claim:{hit['id']}",
            source_kind="claim",
            source_id=str(hit["id"]),
            title=str(hit["title"]),
            domain=str(hit["domain"]),
            score=float(hit["score"]),
            mechanism_similarity=float(hit["mechanism_similarity"]),
            structure_similarity=float(hit["structure_similarity"]),
            problem_shape_similarity=float(hit["problem_shape_similarity"]),
            semantic_similarity=float(hit["semantic_similarity"]),
            domain_distance=float(hit["domain_distance"]),
            failure_overlap=float(hit["failure_overlap"]),
            epistemic_status=str(hit["epistemic_status"]),
            source_type=str(hit["source_type"]),
        )
