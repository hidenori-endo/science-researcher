import unittest

from science_researcher.embeddings import HashEmbedder, cosine_similarity


class HashEmbedderTests(unittest.TestCase):
    def test_is_deterministic(self) -> None:
        embedder = HashEmbedder(64)
        self.assertEqual(embedder.embed("local positivity"), embedder.embed("local positivity"))

    def test_related_text_is_more_similar_than_unrelated_text(self) -> None:
        embedder = HashEmbedder(256)
        anchor = embedder.embed("local positivity analytic rigidity zeros")
        related = embedder.embed("positivity constrains analytic zero rigidity")
        unrelated = embedder.embed("protein folding membrane metabolism")
        self.assertGreater(
            cosine_similarity(anchor, related),
            cosine_similarity(anchor, unrelated),
        )


if __name__ == "__main__":
    unittest.main()
