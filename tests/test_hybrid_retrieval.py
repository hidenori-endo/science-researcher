import io
import tempfile
import unittest
import uuid
from contextlib import redirect_stdout
from pathlib import Path

from science_researcher.cli import main
from science_researcher.embeddings import HashEmbedder
from science_researcher.hybrid_retrieval import HybridRetriever
from science_researcher.models import Evidence, ResearchClaim, ScientificNode
from science_researcher.research import ResearchIndex
from science_researcher.retrieval import MultiAxisRetriever
from science_researcher.service import build_engine, initialize_store


class HybridRetrievalTests(unittest.TestCase):
    def make_store(self, directory: str):
        return initialize_store(str(Path(directory) / "science.db"))

    def make_problem(self) -> ScientificNode:
        return ScientificNode(
            id="problem:test-boundary-limit",
            kind="problem",
            title="Boundary limit problem",
            domain="PDE",
            summary="Pass from a regular parameter regime to a boundary value.",
            mechanism="uniform control across a parameter continuation",
            math_structure="compactness analyticity continuation",
            problem_shape="regular regime to boundary value",
            failure_modes="non-uniform estimates circular limit argument",
        )

    def make_memory_claim(self) -> ResearchClaim:
        return ResearchClaim(
            id=str(uuid.uuid4()),
            external_id="memory-uniform-bound-obstruction",
            title="Uniform estimates are the continuation bottleneck",
            statement="Continuation to a boundary parameter requires estimates uniform in the parameter.",
            record_type="obstruction",
            epistemic_status="mathematically_derived",
            domain="functional analysis",
            axis_texts={
                "mechanism": "uniform control across a parameter continuation",
                "math_structure": "compactness analyticity continuation",
                "problem_shape": "regular regime to boundary value",
                "failure": "non-uniform estimates circular limit argument",
            },
        )

    def test_hybrid_retriever_returns_first_class_research_memory(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            store = self.make_store(directory)
            embedder = HashEmbedder()
            claim = self.make_memory_claim()
            ResearchIndex(store, embedder).index_claim(claim)
            retriever = HybridRetriever(
                store,
                node_retriever=MultiAxisRetriever(store, embedder),
                research_index=ResearchIndex(store, embedder),
            )

            hits = retriever.search(self.make_problem(), limit=5)

            self.assertEqual(len(hits), 1)
            self.assertEqual(hits[0].source_kind, "claim")
            self.assertEqual(hits[0].source_id, claim.id)
            self.assertEqual(hits[0].epistemic_status, "mathematically_derived")
            proxy = store.get_node(hits[0].node_id)
            self.assertEqual(proxy.kind, "research_memory")
            self.assertEqual(proxy.metadata["research_memory_id"], claim.id)

    def test_discovery_uses_memory_and_records_derived_from_relation(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            store = self.make_store(directory)
            embedder = HashEmbedder()
            problem = self.make_problem()
            store.upsert_node(problem)
            claim = self.make_memory_claim()
            index = ResearchIndex(store, embedder)
            index.index_claim(claim)
            evidence = Evidence(
                id=str(uuid.uuid4()),
                title="Finite control observation",
                summary="A finite control reproduces the apparent signature.",
                evidence_type="computational_observation",
                epistemic_status="computational",
                axis_texts={
                    "mechanism": "uniform control across a parameter continuation",
                    "problem_shape": "regular regime to boundary value",
                    "failure": "non-uniform estimates circular limit argument",
                },
                metadata={"domain": "PDE"},
            )
            index.index_evidence(evidence)

            result = build_engine(store, embedder=embedder).run(
                problem.id, candidates_per_reframing=1
            )

            for branch in result["trace"]["branches"]:
                self.assertEqual(branch["analogies"][0]["source_kind"], "claim")
                self.assertEqual(branch["analogies"][0]["source_id"], claim.id)
                self.assertTrue(
                    any(hit["id"] == evidence.id for hit in branch["research_memory"])
                )
                self.assertNotIn(
                    "evidence", {hit["source_kind"] for hit in branch["analogies"]}
                )
            for hypothesis in result["hypotheses"]:
                generated = store.get_claim_with_relations(hypothesis["claim_id"])
                derived = [
                    relation
                    for relation in generated["claim_relations"]
                    if relation["relation"] == "DERIVED_FROM"
                ]
                self.assertEqual(len(derived), 1)
                self.assertEqual(derived[0]["claim"]["id"], claim.id)

    def test_search_research_cli_returns_epistemic_metadata(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            db_path = str(Path(directory) / "science.db")
            store = initialize_store(db_path)
            claim = self.make_memory_claim()
            ResearchIndex(store, HashEmbedder()).index_claim(claim)

            output = io.StringIO()
            with redirect_stdout(output):
                exit_code = main(
                    [
                        "search-research",
                        "--db",
                        db_path,
                        "--query",
                        "uniform control across a parameter continuation",
                        "--mechanism",
                        "uniform control across a parameter continuation",
                        "--domain",
                        "PDE",
                        "--entity-kind",
                        "claim",
                        "--limit",
                        "3",
                    ]
                )

            self.assertEqual(exit_code, 0)
            self.assertIn(claim.id, output.getvalue())
            self.assertIn("mathematically_derived", output.getvalue())
            self.assertIn("obstruction", output.getvalue())


if __name__ == "__main__":
    unittest.main()
