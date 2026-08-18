import unittest

from science_researcher.postgres_store import _parse_vector, _vector_literal


class PostgresStoreHelpersTests(unittest.TestCase):
    def test_vector_literal_round_trips(self) -> None:
        vector = [0.0, 1.25, -2.5]
        self.assertEqual(_parse_vector(_vector_literal(vector)), vector)


if __name__ == "__main__":
    unittest.main()
