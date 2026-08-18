import tempfile
import unittest
from pathlib import Path

from science_researcher.service import build_engine, initialize_store, seed_store


class PipelineTests(unittest.TestCase):
    def test_demo_persists_hypotheses_and_obligations(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            db_path = str(Path(directory) / "science.db")
            store = initialize_store(db_path)
            seed_store(store)
            result = build_engine(store).run("problem:riemann-hypothesis", candidates_per_reframing=2)

            self.assertEqual(result["problem_id"], "problem:riemann-hypothesis")
            self.assertGreaterEqual(len(result["hypotheses"]), 2)
            for hypothesis in result["hypotheses"]:
                self.assertGreaterEqual(len(hypothesis["proof_obligations"]), 1)

    def test_runs_are_auditable(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            db_path = str(Path(directory) / "science.db")
            store = initialize_store(db_path)
            seed_store(store)
            result = build_engine(store).run("problem:navier-stokes", candidates_per_reframing=1)
            loaded = store.get_run(result["id"])
            self.assertIn("branches", loaded["trace"])
            self.assertEqual(loaded["id"], result["id"])


if __name__ == "__main__":
    unittest.main()
