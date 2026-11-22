import json
import unittest
from types import SimpleNamespace
from unittest.mock import patch

from llm_api import NO_INFORMATION, ask


class AnswerTests(unittest.TestCase):
    def test_revision_filename_is_not_sent_as_evidence(self):
        chunk = {
            "id": "founding", "document": "revision-2024.pdf", "section": "Page 2",
            "page": 2, "text": "Η εταιρεία συστάθηκε με το ν.3489/2006.",
        }
        response = SimpleNamespace(message=SimpleNamespace(content=json.dumps({
            "answer": chunk["text"], "source_numbers": [1],
        })))
        with patch("llm_api.retrieve", return_value=[chunk]), patch("llm_api.Client") as client:
            client.return_value.chat.return_value = response
            result = ask("Ποτε ιδρύθηκε η εταιρεια ;", [chunk])
        prompt = client.return_value.chat.call_args.kwargs["messages"][1]["content"]
        self.assertIn(chunk["text"], prompt)
        self.assertNotIn("revision-2024.pdf", prompt)
        self.assertEqual(result["sources"][0]["document"], "revision-2024.pdf")
        self.assertEqual(result["sources"][0]["page"], 2)

    def test_no_matches_does_not_call_the_model(self):
        with patch("llm_api.retrieve", return_value=[]), patch("llm_api.Client") as client:
            with self.assertLogs("uvicorn.error", level="INFO") as logs:
                result = ask("αστροναύτες", [])
        client.assert_not_called()
        self.assertEqual(result, {"answer": NO_INFORMATION, "sources": []})
        self.assertIn("retrieval found no matching", logs.output[0])


if __name__ == "__main__":
    unittest.main()
