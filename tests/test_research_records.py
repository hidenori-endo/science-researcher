import json
import sqlite3
import tempfile
import unittest
import uuid
from pathlib import Path

from science_researcher.models import Evidence, ResearchClaim
from science_researcher.postgres_store import POSTGRES_SCHEMA
from science_researcher.research import ResearchIndex
from science_researcher.service import build_engine, initialize_store, seed_store


class RecordingEmbedder:
    def __init__(self) -> None:
        self.inputs: list[str] = []

    def embed(self, text: str) -> list[float]:
        self.inputs.append(text)
        return [float(len(text)), 1.0]


class ResearchRecordTests(unittest.TestCase):
    def make_store(self, directory: str):
        return initialize_store(str(Path(directory) / "science.db"))

    def test_create_claim_evidence_link_and_retrieve(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            store = self.make_store(directory)
            claim = ResearchClaim(
                id=str(uuid.uuid4()),
                title="Uniform bound obstruction",
                statement="The limiting argument needs a parameter-uniform estimate.",
                record_type="obstruction",
                epistemic_status="mathematically_derived",
                domain="PDE",
            )
            evidence = Evidence(
                id=str(uuid.uuid4()),
                title="Compactness requirement",
                summary="Passing to the boundary parameter requires compactness and norm control.",
                evidence_type="theorem",
                epistemic_status="mathematically_derived",
            )
            store.upsert_research_claim(claim)
            store.upsert_evidence(evidence)
            relation_id = store.link_evidence(claim.id, evidence.id, "SUPPORTS")

            loaded = store.get_claim_with_relations(claim.id)
            self.assertEqual(loaded["id"], claim.id)
            self.assertEqual(len(loaded["evidence"]), 1)
            self.assertEqual(loaded["evidence"][0]["id"], relation_id)
            self.assertEqual(loaded["evidence"][0]["relation"], "SUPPORTS")
            self.assertEqual(loaded["evidence"][0]["evidence"]["id"], evidence.id)

    def test_invalid_status_and_relation_are_rejected(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            store = self.make_store(directory)
            bad_claim = ResearchClaim(
                id=str(uuid.uuid4()),
                title="Bad status",
                statement="This must not be accepted as proof.",
                record_type="hypothesis",
                epistemic_status="proved-by-python",
                domain="test",
            )
            with self.assertRaises(ValueError):
                store.upsert_research_claim(bad_claim)

            claim = ResearchClaim(
                id=str(uuid.uuid4()),
                title="Claim",
                statement="A claim.",
                record_type="hypothesis",
                epistemic_status="conjectural",
                domain="test",
            )
            evidence = Evidence(
                id=str(uuid.uuid4()),
                title="Evidence",
                summary="A computation.",
                evidence_type="computational_observation",
                epistemic_status="computational",
            )
            store.upsert_research_claim(claim)
            store.upsert_evidence(evidence)
            with self.assertRaises(ValueError):
                store.link_evidence(claim.id, evidence.id, "PROVES")

    def test_versioned_bundle_import_is_idempotent_and_transactional(self) -> None:
        bundle = {
            "schema_version": 1,
            "claims": [
                {
                    "external_id": "claim-1",
                    "title": "Imported hypothesis",
                    "statement": "A tentative bridge exists.",
                    "record_type": "hypothesis",
                    "epistemic_status": "conjectural",
                    "domain": "test",
                }
            ],
            "evidence": [
                {
                    "external_id": "evidence-1",
                    "title": "Control observation",
                    "summary": "The control weakens the bridge.",
                    "evidence_type": "computational_observation",
                    "epistemic_status": "computational",
                }
            ],
            "relations": [
                {
                    "claim": "claim-1",
                    "evidence": "evidence-1",
                    "relation": "WEAKENS",
                }
            ],
        }
        with tempfile.TemporaryDirectory() as directory:
            store = self.make_store(directory)
            first = store.import_research_bundle(bundle)
            second = store.import_research_bundle(bundle)
            self.assertEqual(first["claims"], second["claims"])
            self.assertEqual(first["evidence"], second["evidence"])
            self.assertEqual(len(store.list_research_claims()), 1)
            self.assertEqual(len(store.list_evidence()), 1)
            loaded = store.get_claim_with_relations(first["claims"]["claim-1"])
            self.assertEqual(len(loaded["evidence"]), 1)

            invalid = json.loads(json.dumps(bundle))
            invalid["claims"][0]["epistemic_status"] = "proved-by-numerics"
            with self.assertRaises(ValueError):
                store.import_research_bundle(invalid)
            self.assertEqual(len(store.list_research_claims()), 1)

    def test_research_index_uses_axis_specific_canonical_text(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            store = self.make_store(directory)
            embedder = RecordingEmbedder()
            claim = ResearchClaim(
                id=str(uuid.uuid4()),
                title="Axis-specific claim",
                statement="Semantic statement.",
                record_type="hypothesis",
                epistemic_status="conjectural",
                domain="domain canonical",
                axis_texts={
                    "mechanism": "mechanism canonical",
                    "math_structure": "math canonical",
                    "problem_shape": "shape canonical",
                    "failure": "failure canonical",
                },
            )
            ResearchIndex(store, embedder).index_claim(claim)

            self.assertEqual(len(embedder.inputs), 6)
            self.assertEqual(len(set(embedder.inputs)), 6)
            self.assertIn("mechanism canonical", embedder.inputs)
            self.assertIn("failure canonical", embedder.inputs)
            for axis in ("semantic", "domain", "mechanism", "math_structure", "problem_shape", "failure"):
                self.assertEqual(len(store.get_research_vector("claim", claim.id, axis)), 2)

    def test_claims_and_evidence_participate_in_research_retrieval(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            store = self.make_store(directory)
            index = ResearchIndex(store, RecordingEmbedder())
            claim = ResearchClaim(
                id=str(uuid.uuid4()),
                title="Claim",
                statement="A structural bridge.",
                record_type="hypothesis",
                epistemic_status="conjectural",
                domain="PDE",
                axis_texts={"mechanism": "uniform control", "problem_shape": "boundary limit"},
            )
            evidence = Evidence(
                id=str(uuid.uuid4()),
                title="Evidence",
                summary="A limiting observation.",
                evidence_type="computational_observation",
                epistemic_status="computational",
                axis_texts={"mechanism": "uniform control", "problem_shape": "boundary limit"},
                metadata={"domain": "statistical mechanics"},
            )
            index.index_claim(claim)
            index.index_evidence(evidence)
            hits = index.search(claim, limit=10)
            self.assertEqual({hit["id"] for hit in hits}, {claim.id, evidence.id})

    def test_sqlite_initialize_migrates_existing_hypotheses_table(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            db_path = str(Path(directory) / "legacy.db")
            with sqlite3.connect(db_path) as connection:
                connection.execute(
                    """
                    CREATE TABLE hypotheses (
                        id TEXT PRIMARY KEY,
                        run_id TEXT NOT NULL,
                        problem_id TEXT NOT NULL,
                        analogy_node_id TEXT NOT NULL,
                        title TEXT NOT NULL,
                        bridge TEXT NOT NULL,
                        prediction TEXT NOT NULL,
                        rationale TEXT NOT NULL,
                        status TEXT NOT NULL,
                        critic_score REAL NOT NULL,
                        failure_reason TEXT NOT NULL DEFAULT ''
                    )
                    """
                )
            store = initialize_store(db_path)
            with store.connect() as connection:
                columns = {
                    row["name"] for row in connection.execute("PRAGMA table_info(hypotheses)")
                }
            self.assertIn("claim_id", columns)

    def test_generated_hypotheses_link_to_canonical_research_claims(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            store = self.make_store(directory)
            seed_store(store)
            result = build_engine(store).run("problem:navier-stokes", candidates_per_reframing=1)
            loaded = store.get_run(result["id"])
            self.assertGreaterEqual(len(loaded["hypotheses"]), 1)
            for hypothesis in loaded["hypotheses"]:
                self.assertIsNotNone(hypothesis["claim_id"])
                claim = store.get_research_claim(hypothesis["claim_id"])
                self.assertEqual(claim.record_type, "hypothesis")
                self.assertIn(claim.epistemic_status, ("conjectural", "speculative"))
                self.assertGreater(len(store.get_research_vector("claim", claim.id, "semantic")), 0)

    def test_initial_research_bundle_smoke_import(self) -> None:
        bundle_path = Path(__file__).parents[1] / "research" / "initial-research.json"
        bundle = json.loads(bundle_path.read_text(encoding="utf-8"))
        with tempfile.TemporaryDirectory() as directory:
            store = self.make_store(directory)
            result = store.import_research_bundle(bundle)
            self.assertGreaterEqual(len(result["claims"]), 10)
            self.assertGreaterEqual(len(result["evidence"]), 5)
            self.assertGreaterEqual(result["relations"], 10)

    def test_postgres_schema_extends_existing_neon_store(self) -> None:
        self.assertIn("CREATE TABLE IF NOT EXISTS research_claims", POSTGRES_SCHEMA)
        self.assertIn("CREATE TABLE IF NOT EXISTS evidences", POSTGRES_SCHEMA)
        self.assertIn("CREATE TABLE IF NOT EXISTS research_relations", POSTGRES_SCHEMA)
        self.assertIn("CREATE TABLE IF NOT EXISTS research_vectors", POSTGRES_SCHEMA)
        self.assertIn("ADD COLUMN IF NOT EXISTS claim_id", POSTGRES_SCHEMA)
        self.assertIn("vector vector NOT NULL", POSTGRES_SCHEMA)


if __name__ == "__main__":
    unittest.main()
