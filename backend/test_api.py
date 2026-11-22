import unittest
from unittest.mock import patch

from fastapi.testclient import TestClient

from main import app
from vector_search import EmbeddingIndexError


class ApiTests(unittest.TestCase):
    def setUp(self):
        self.client = TestClient(app)

    def test_answer_and_sources(self):
        expected = {
            "answer": "Θεσσαλονίκη",
            "sources": [{"document": "example.pdf", "section": "Page 3", "page": 3}],
        }
        with patch("main.ask", return_value=expected) as ask:
            response = self.client.post("/ask", json={"question": "  Ποια είναι η έδρα;  "})
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json(), expected)
        self.assertEqual(ask.call_args.args[0], "Ποια είναι η έδρα;")

    def test_invalid_questions(self):
        with patch("main.ask") as ask:
            for body in [{}, {"question": ""}, {"question": "   "},
                         {"question": 123}, {"question": "x" * 2001}]:
                with self.subTest(body=body):
                    response = self.client.post("/ask", json=body)
                    self.assertEqual(response.status_code, 422)
            ask.assert_not_called()

    def test_no_information(self):
        response = self.client.post("/ask", json={"question": "αστροναύτες"})
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json()["sources"], [])
        self.assertIn("do not contain", response.json()["answer"])

    def test_ollama_unavailable(self):
        with patch("main.ask", side_effect=ConnectionError("offline")):
            response = self.client.post("/ask", json={"question": "έδρα"})
        self.assertEqual(response.status_code, 503)

    def test_invalid_model_output(self):
        with patch("main.ask", side_effect=ValueError("invalid citation")):
            response = self.client.post("/ask", json={"question": "έδρα"})
        self.assertEqual(response.status_code, 502)

    def test_search_modes_are_passed_to_answer_function(self):
        for mode in ["bm25", "vector", "hybrid"]:
            with self.subTest(mode=mode), patch("main.ask", return_value={
                    "answer": "Example", "sources": []}) as ask:
                response = self.client.post("/ask", json={"question": "έδρα", "search_mode": mode})
                self.assertEqual(response.status_code, 200)
                self.assertEqual(ask.call_args.kwargs["search_mode"], mode)

    def test_existing_clients_keep_bm25_by_default(self):
        with patch("main.ask", return_value={"answer": "Example", "sources": []}) as ask:
            self.client.post("/ask", json={"question": "έδρα"})
        self.assertEqual(ask.call_args.kwargs["search_mode"], "bm25")

    def test_unknown_search_mode_is_rejected(self):
        response = self.client.post("/ask", json={"question": "έδρα", "search_mode": "unknown"})
        self.assertEqual(response.status_code, 422)

    def test_vector_index_setup_error_is_actionable(self):
        with patch("main.ask", side_effect=EmbeddingIndexError("missing index")):
            response = self.client.post("/ask", json={"question": "έδρα", "search_mode": "vector"})
        self.assertEqual(response.status_code, 503)
        self.assertIn("vector_search.py", response.json()["detail"])


if __name__ == "__main__":
    unittest.main()
