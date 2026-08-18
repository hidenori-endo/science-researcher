from __future__ import annotations

from dataclasses import dataclass

from .db import GraphStore
from .embeddings import HashEmbedder, cosine_similarity, overlap_ratio
from .models import AnalogyCandidate, ScientificNode


AXES = ("semantic", "domain", "mechanism", "math_structure", "problem_shape", "failure")


@dataclass(slots=True)
class RetrievalWeights:
    mechanism: float = 0.50
    math_structure: float = 0.20
    problem_shape: float = 0.15
    semantic: float = 0.15
    domain_distance: float = 0.20
    failure_overlap_penalty: float = 0.20


class MultiAxisRetriever:
    def __init__(
        self,
        store: GraphStore,
        embedder: HashEmbedder | None = None,
        weights: RetrievalWeights | None = None,
    ) -> None:
        self.store = store
        self.embedder = embedder or HashEmbedder()
        self.weights = weights or RetrievalWeights()

    def index_node(self, node: ScientificNode) -> None:
        self.store.upsert_node(node)
        for axis in AXES:
            self.store.put_vector(node.id, axis, self.embedder.embed(node.axis_text(axis)))

    def search(
        self,
        query: ScientificNode,
        *,
        kind: str = "breakthrough",
        limit: int = 5,
    ) -> list[AnalogyCandidate]:
        query_vectors = {axis: self.embedder.embed(query.axis_text(axis)) for axis in AXES}
        candidates: list[AnalogyCandidate] = []
        for node in self.store.list_nodes(kind=kind):
            similarities = {
                axis: cosine_similarity(query_vectors[axis], self.store.get_vector(node.id, axis))
                for axis in AXES
            }
            domain_similarity = max(0.0, similarities["domain"])
            domain_distance = 1.0 - domain_similarity
            failure_overlap = overlap_ratio(query.failure_modes, node.failure_modes)

            score = (
                self.weights.mechanism * similarities["mechanism"]
                + self.weights.math_structure * similarities["math_structure"]
                + self.weights.problem_shape * similarities["problem_shape"]
                + self.weights.semantic * similarities["semantic"]
                + self.weights.domain_distance * domain_distance
                - self.weights.failure_overlap_penalty * failure_overlap
            )
            candidates.append(
                AnalogyCandidate(
                    node_id=node.id,
                    title=node.title,
                    domain=node.domain,
                    score=score,
                    mechanism_similarity=similarities["mechanism"],
                    structure_similarity=similarities["math_structure"],
                    problem_shape_similarity=similarities["problem_shape"],
                    semantic_similarity=similarities["semantic"],
                    domain_distance=domain_distance,
                    failure_overlap=failure_overlap,
                )
            )

        candidates.sort(key=lambda item: item.score, reverse=True)
        return candidates[:limit]
