import json
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from hybrid_search import fuse_rankings, retrieve
from vector_search import INDEX_VERSION, MODEL, fingerprint, load_index, rank_vectors, unit_vector


class VectorSearchTests(unittest.TestCase):
    def test_cosine_ranking_preserves_source_metadata(self):
        chunks = [{"id": "a", "text": "first", "document": "a.pdf", "page": 2},
                  {"id": "b", "text": "second", "document": "b.pdf", "page": 4}]
        results = rank_vectors(chunks, [[3, 0], [0, 2]], [2, 0], min_similarity=0.5)
        self.assertEqual([r["id"] for r in results], ["a"])
        self.assertEqual(results[0]["page"], 2)
        self.assertAlmostEqual(results[0]["similarity"], 1)

    def test_low_similarity_does_not_force_a_match(self):
        self.assertEqual(rank_vectors([{"id": "a"}], [[1, 0]], [0, 1]), [])

    def test_bad_vectors_are_rejected(self):
        for vector in [[], [0, 0], [float("nan")], [float("inf")]]:
            with self.subTest(vector=vector), self.assertRaises(ValueError):
                unit_vector(vector)
        with self.assertRaises(ValueError):
            rank_vectors([{"id": "a"}], [[1, 0]], [1, 0, 0])

    def test_changed_text_metadata_or_order_invalidates_index(self):
        chunks = [{"id": "a", "text": "original", "page": 1},
                  {"id": "b", "text": "other", "page": 2}]
        index = {"version": INDEX_VERSION, "model": MODEL, "fingerprint": fingerprint(chunks),
                 "dimension": 2, "vectors": [[1, 0], [0, 1]]}
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "index.json"
            path.write_text(json.dumps(index))
            self.assertEqual(load_index(chunks, path)["dimension"], 2)
            variants = [list(reversed(chunks)), [{**chunks[0], "text": "changed"}, chunks[1]],
                        [{**chunks[0], "page": 3}, chunks[1]]]
            for changed in variants:
                with self.subTest(changed=changed), self.assertRaises(ValueError):
                    load_index(changed, path)

    def test_fusion_rewards_agreement_and_ignores_raw_score_scales(self):
        keywords = [{"id": "b", "score": 1000}, {"id": "a", "score": 0.1}]
        vectors = [{"id": "c", "score": 0.99}, {"id": "b", "score": 0.8}]
        results = fuse_rankings(keywords, vectors)
        self.assertEqual(results[0]["id"], "b")
        changed_scores = [{**result, "score": -99999} for result in keywords]
        self.assertEqual(results, fuse_rankings(changed_scores, vectors))

    def test_bm25_candidate_is_not_removed_by_vector_ranking(self):
        results = fuse_rankings([{"id": "keyword"}], [{"id": "semantic"}])
        self.assertEqual(results[0]["id"], "keyword")
        self.assertEqual({r["id"] for r in results}, {"keyword", "semantic"})

    def test_duplicate_ids_do_not_receive_extra_votes(self):
        single = [{"id": "a"}]
        self.assertEqual(fuse_rankings(single, single)[0]["score"],
                         fuse_rankings(single * 2, single * 2)[0]["score"])

    def test_no_semantic_support_returns_no_passages(self):
        with patch("hybrid_search.bm25_retrieve", return_value=[{"id": "a"}]), \
                patch("hybrid_search.vector_retrieve", return_value=[]):
            self.assertEqual(retrieve("κωδικός εταιρείας", [{"text": "εταιρεία"}]), [])

    def test_missing_index_falls_back_to_bm25_with_warning(self):
        expected = [{"id": "a"}]
        with patch("hybrid_search.bm25_retrieve", return_value=expected), \
                patch("hybrid_search.vector_retrieve", side_effect=FileNotFoundError("index")), \
                self.assertLogs("uvicorn.error", level="WARNING") as logs:
            self.assertEqual(retrieve("έδρα", [{"text": "έδρα"}]), expected)
        self.assertIn("using BM25", logs.output[0])

    def test_common_words_do_not_call_ollama(self):
        with patch("hybrid_search.vector_retrieve") as search:
            self.assertEqual(retrieve("της τους", [{"text": "anything"}]), [])
            search.assert_not_called()


if __name__ == "__main__":
    unittest.main()
