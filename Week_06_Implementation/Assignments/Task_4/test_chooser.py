import unittest

from chooser import choose_chunks, cosine_similarity


class CosineSimilarityTests(unittest.TestCase):
    def test_similarity_uses_vector_direction(self):
        self.assertAlmostEqual(cosine_similarity([1, 1], [2, 2]), 1.0)
        self.assertAlmostEqual(cosine_similarity([1, 0], [0, 1]), 0.0)
        self.assertAlmostEqual(cosine_similarity([1, 0], [-1, 0]), -1.0)

    def test_zero_vector_similarity_is_zero(self):
        self.assertEqual(cosine_similarity([0, 0], [1, 2]), 0.0)

    def test_mismatched_dimensions_are_rejected(self):
        with self.assertRaisesRegex(ValueError, "dimension mismatch"):
            cosine_similarity([1, 2], [1])


class ChooseChunksTests(unittest.TestCase):
    def setUp(self):
        self.storage = {
            "dimensions": 2,
            "embeddings": [
                {"id": "parallel", "embedding": [1, 1], "path": "parallel.py"},
                {"id": "opposite", "embedding": [-1, 0], "path": "opposite.py"},
                {"id": "orthogonal", "embedding": [0, 1], "path": "orthogonal.py"},
            ],
        }

    def test_returns_top_n_descending_by_similarity(self):
        results = choose_chunks([1, 0], self.storage, 2)
        self.assertEqual([result["id"] for result in results], ["parallel", "orthogonal"])
        self.assertGreaterEqual(
            results[0]["similarity"], results[1]["similarity"]
        )

    def test_n_larger_than_storage_returns_all(self):
        self.assertEqual(len(choose_chunks([1, 0], self.storage, 10)), 3)

    def test_zero_n_returns_empty(self):
        self.assertEqual(choose_chunks([1, 0], self.storage, 0), [])

    def test_negative_n_is_rejected(self):
        with self.assertRaisesRegex(ValueError, "n must not be negative"):
            choose_chunks([1, 0], self.storage, -1)

    def test_query_dimension_must_match_storage(self):
        with self.assertRaisesRegex(ValueError, "dimension mismatch"):
            choose_chunks([1], self.storage, 1)

    def test_ties_keep_storage_order(self):
        tied_storage = {
            "dimensions": 2,
            "embeddings": [
                {"id": "first", "embedding": [1, 0]},
                {"id": "second", "embedding": [2, 0]},
            ],
        }
        results = choose_chunks([1, 0], tied_storage, 2)
        self.assertEqual([result["id"] for result in results], ["first", "second"])

    def test_exact_symbol_name_match_boosts_implementation_chunk(self):
        symbol_storage = {
            "dimensions": 2,
            "embeddings": [
                {
                    "id": "test",
                    "embedding": [1, 0],
                    "path": "tests/test_pricing.py",
                    "kind": "class",
                    "name": "BulkDiscountConstructionTests",
                },
                {
                    "id": "implementation",
                    "embedding": [0.8, 0.6],
                    "path": "playground/pricing.py",
                    "kind": "class",
                    "name": "BulkDiscountPricing",
                },
            ],
        }
        results = choose_chunks(
            [1, 0], symbol_storage, 2, query_text="Where is BulkDiscountPricing implemented?"
        )
        self.assertEqual(results[0]["id"], "implementation")
        self.assertGreater(results[0]["score"], results[1]["score"])
        self.assertLess(results[0]["similarity"], results[1]["similarity"])


if __name__ == "__main__":
    unittest.main()
