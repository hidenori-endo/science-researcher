from __future__ import annotations

from abc import ABC, abstractmethod

from .embeddings import overlap_ratio
from .models import Critique, HypothesisDraft, ProofObligation, Reframing, ScientificNode


class ReasoningProvider(ABC):
    """Boundary for LLM-backed reasoning stages.

    Production implementations can call any model provider. Keeping this interface
    small makes generator/critic isolation explicit and keeps the core engine testable.
    """

    @abstractmethod
    def reframe(self, problem: ScientificNode) -> list[Reframing]:
        raise NotImplementedError

    @abstractmethod
    def mutate(
        self,
        problem: ScientificNode,
        reframing: Reframing,
        analogy: ScientificNode,
    ) -> HypothesisDraft:
        raise NotImplementedError

    @abstractmethod
    def critique(
        self,
        problem: ScientificNode,
        analogy: ScientificNode,
        hypothesis: HypothesisDraft,
    ) -> Critique:
        raise NotImplementedError

    @abstractmethod
    def extract_obligations(
        self,
        problem: ScientificNode,
        analogy: ScientificNode,
        hypothesis: HypothesisDraft,
        critique: Critique,
    ) -> list[ProofObligation]:
        raise NotImplementedError


class HeuristicProvider(ReasoningProvider):
    """Deterministic provider used by the offline MVP and CI.

    It models the shape of the discovery loop without pretending to replace an LLM.
    The output is intentionally inspectable and reproducible.
    """

    def reframe(self, problem: ScientificNode) -> list[Reframing]:
        return [
            Reframing(
                label="mechanistic",
                text=f"Find a mechanism that changes the tractability of: {problem.summary}",
                mechanism_query=problem.mechanism,
                structure_query=problem.math_structure,
                problem_shape_query=problem.problem_shape,
                forbidden_shortcuts=["assume the desired conclusion", "rename the original hard step"],
            ),
            Reframing(
                label="obstruction",
                text=f"Turn the target into a minimal obstruction problem: {problem.summary}",
                mechanism_query=f"obstruction certificate {problem.mechanism}",
                structure_query=f"rigidity certificate {problem.math_structure}",
                problem_shape_query=f"existence to obstruction {problem.problem_shape}",
                forbidden_shortcuts=["non-uniform limit", "circular reformulation"],
            ),
        ]

    def mutate(
        self,
        problem: ScientificNode,
        reframing: Reframing,
        analogy: ScientificNode,
    ) -> HypothesisDraft:
        bridge = (
            f"Abstract the enabling move in '{analogy.title}' as [{analogy.mechanism}] and seek a "
            f"target-specific certificate inside '{problem.title}' that supplies the same enabling "
            "structure without importing the source-domain object literally."
        )
        prediction = (
            f"If the bridge exists, a finite or local certificate should constrain the target's "
            f"global behavior through {analogy.math_structure}."
        )
        rationale = (
            f"The candidate is selected because the structural problem shape '{problem.problem_shape}' "
            f"is being matched to the distant-domain mechanism '{analogy.mechanism}', not because the "
            "topics are semantically adjacent."
        )
        return HypothesisDraft(
            title=f"{problem.title} via mutated {analogy.title} mechanism",
            bridge=bridge,
            prediction=prediction,
            rationale=rationale,
            source_node_id=analogy.id,
        )

    def critique(
        self,
        problem: ScientificNode,
        analogy: ScientificNode,
        hypothesis: HypothesisDraft,
    ) -> Critique:
        checks = [
            "Does the bridge preserve the enabling structure of the source theorem?",
            "Does any assumption already encode the target conclusion?",
            "Can the bridge be falsified on a finite or toy instance?",
            "Does a limit exchange require a uniform bound equivalent to the original problem?",
        ]
        failure_overlap = overlap_ratio(problem.failure_modes, analogy.failure_modes)
        if failure_overlap >= 0.15:
            return Critique(
                score=0.35,
                verdict="weak",
                failure_reason="The source and target share an explicit known failure mode; test that obstruction first.",
                checks=checks,
            )
        return Critique(
            score=0.72,
            verdict="test",
            failure_reason="No immediate structural contradiction is encoded in the seed knowledge; this is not evidence of truth.",
            checks=checks,
        )

    def extract_obligations(
        self,
        problem: ScientificNode,
        analogy: ScientificNode,
        hypothesis: HypothesisDraft,
        critique: Critique,
    ) -> list[ProofObligation]:
        return [
            ProofObligation(
                statement=(
                    f"Define an explicit target-side object for '{problem.title}' that realizes the "
                    f"enabling structure: {analogy.math_structure}."
                ),
                verification_method="construct-or-counterexample",
            ),
            ProofObligation(
                statement=(
                    "Prove that the proposed object satisfies the source mechanism's essential hypotheses "
                    "without assuming the target conclusion."
                ),
                verification_method="theorem-proof",
            ),
            ProofObligation(
                statement=(
                    f"Show that the preserved mechanism actually implies a nontrivial constraint on "
                    f"the target problem shape: {problem.problem_shape}."
                ),
                verification_method="theorem-proof",
            ),
            ProofObligation(
                statement="Search the smallest finite/toy instance for a counterexample before scaling up.",
                verification_method="python-falsification",
            ),
        ]
