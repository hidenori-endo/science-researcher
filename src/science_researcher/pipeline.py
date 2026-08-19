from __future__ import annotations

from dataclasses import asdict
from typing import Any

from .db import GraphStore
from .hybrid_retrieval import HybridRetriever
from .models import ScientificNode
from .provider import ReasoningProvider
from .research import ResearchIndex


class DiscoveryEngine:
    def __init__(
        self,
        *,
        store: GraphStore,
        retriever: HybridRetriever,
        generator: ReasoningProvider,
        critic: ReasoningProvider,
    ) -> None:
        self.store = store
        self.retriever = retriever
        self.generator = generator
        self.critic = critic

    def run(self, problem_id: str, *, candidates_per_reframing: int = 3) -> dict[str, Any]:
        problem = self.store.get_node(problem_id)
        if problem.kind != "problem":
            raise ValueError(f"{problem_id} is not a problem node")

        run_id = self.store.create_run(problem_id)
        reframings = self.generator.reframe(problem)
        trace: dict[str, Any] = {
            "problem": problem.to_dict(),
            "reframings": [asdict(item) for item in reframings],
            "branches": [],
        }

        for reframing in reframings:
            query = ScientificNode(
                id=f"query:{run_id}:{reframing.label}",
                kind="query",
                title=problem.title,
                domain=problem.domain,
                summary=reframing.text,
                mechanism=reframing.mechanism_query,
                math_structure=reframing.structure_query,
                problem_shape=reframing.problem_shape_query,
                failure_modes=problem.failure_modes,
            )
            retrieval = self.retriever.retrieve(query, limit=candidates_per_reframing)
            analogies = retrieval.analogies

            branch = {
                "reframing": reframing.label,
                "analogies": [asdict(item) for item in analogies],
                "research_memory": retrieval.research_memory,
                "hypotheses": [],
            }

            for analogy_score in analogies:
                analogy = self.retriever.contextualize(
                    self.store.get_node(analogy_score.node_id), retrieval.research_memory
                )
                draft = self.generator.mutate(problem, reframing, analogy)
                critique = self.critic.critique(problem, analogy, draft)
                obligations = self.critic.extract_obligations(problem, analogy, draft, critique)
                status = "candidate" if critique.score >= 0.5 else "rejected"

                hypothesis_id = self.store.save_hypothesis(
                    run_id=run_id,
                    problem_id=problem.id,
                    analogy_node_id=analogy.id,
                    title=draft.title,
                    bridge=draft.bridge,
                    prediction=draft.prediction,
                    rationale=draft.rationale,
                    status=status,
                    critic_score=critique.score,
                    failure_reason=critique.failure_reason,
                    obligations=obligations,
                )
                generated_claim = self.store.get_hypothesis_claim(hypothesis_id)
                ResearchIndex(self.store, self.retriever.embedder).index_existing_claim(generated_claim)
                memory_kind = analogy.metadata.get("research_memory_kind")
                memory_id = analogy.metadata.get("research_memory_id")
                if memory_kind == "claim" and isinstance(memory_id, str):
                    self.store.link_claims(generated_claim.id, memory_id, "DERIVED_FROM")
                elif memory_kind == "evidence" and isinstance(memory_id, str):
                    self.store.link_evidence(generated_claim.id, memory_id, "MOTIVATES")
                branch["hypotheses"].append(
                    {
                        "id": hypothesis_id,
                        "analogy": analogy.title,
                        "draft": asdict(draft),
                        "critique": asdict(critique),
                        "proof_obligations": [asdict(item) for item in obligations],
                    }
                )
            trace["branches"].append(branch)

        self.store.update_run_trace(run_id, trace)
        return self.store.get_run(run_id)
