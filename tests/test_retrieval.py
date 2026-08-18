import tempfile
import unittest
from pathlib import Path

from science_researcher.models import ScientificNode
from science_researcher.retrieval import MultiAxisRetriever
from science_researcher.service import initialize_store, seed_store


class RetrievalTests(unittest.TestCase):
    def test_returns_domain_distant_structural_candidates(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            store = initialize_store(str(Path(directory) / "science.db"))
            seed_store(store)
            retriever = MultiAxisRetriever(store)
            query = ScientificNode(
                id="query",
                kind="query",
                title="zero rigidity",
                domain="analytic number theory",
                summary="force zeros onto a constrained locus",
                mechanism="local positivity constrains global analytic zero geometry",
                math_structure="positivity analyticity zeros",
                problem_shape="local to global coefficient structure to zero location",
                failure_modes="circular reformulation",
            )
            results = retriever.search(query, limit=3)
            ids = {result.node_id for result in results}
            self.assertIn("breakthrough:lee-yang", ids)


if __name__ == "__main__":
    unittest.main()
