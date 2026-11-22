import json
import unittest

from retrieve import CHUNKS_FILE, query_terms, retrieve, tokenize


class RetrievalTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.chunks = json.loads(CHUNKS_FILE.read_text(encoding="utf-8"))

    def test_greek_stop_words_are_removed_after_casefold(self):
        self.assertEqual(tokenize("της τους τις της"), [])

    def test_when_question_does_not_match_never(self):
        self.assertEqual(tokenize("Πότε ποτέ ποτε"), [])

    def test_company_founding_question_ranks_establishment_passage_first(self):
        for question in ["Ποτε ιδρύθηκε η εταιρεια ;", "Πότε ιδρύθηκε η εταιρεία;"]:
            with self.subTest(question=question):
                results = retrieve(question, self.chunks)
                self.assertEqual(results[0]["document"], "2024_Καταστατικό-ΑΖΚ.pdf")
                self.assertEqual(results[0]["page"], 2)
                self.assertIn("συστάθηκε η", results[0]["text"])
                self.assertIn("3489/2006", results[0]["text"])

    def test_purpose_and_duration_passages_remain_retrievable(self):
        cases = [
            ("Ποιος είναι ο σκοπός της εταιρείας;", "Σκοπός της Εταιρείας, σύμφωνα"),
            ("Ποια είναι η διάρκεια της εταιρείας;", "Η διάρκεια της Εταιρείας ορίζεται"),
        ]
        for question, expected_text in cases:
            with self.subTest(question=question):
                results = retrieve(question, self.chunks)
                self.assertTrue(any(expected_text in r["text"] for r in results))

    def test_accents_and_capitalization_do_not_change_tokens(self):
        self.assertEqual(tokenize("ΟΡΓΆΝΩΣΗ ΕΤΑΙΡΕΊΑΣ"), tokenize("οργανωση εταιρειας"))

    def test_greek_inflections_match(self):
        self.assertEqual(tokenize("εταιρεία"), tokenize("εταιρείας"))
        self.assertEqual(tokenize("οργανωτική"), tokenize("οργανωτικής"))

    def test_related_organization_terms_are_expanded(self):
        self.assertTrue(set(tokenize("οργανωτική διάρθρωση οργανόγραμμα"))
                        <= query_terms("οργάνωση"))

    def test_user_organization_question_ranks_structure_first(self):
        for question in ["Ποια ειναι η οργανωση της εταιρειας;",
                         "Ποια είναι η οργάνωση της εταιρείας;"]:
            with self.subTest(question=question):
                results = retrieve(question, self.chunks)
                self.assertEqual(results[0]["document"], "kanonismos_fixed.pdf")
                self.assertEqual(results[0]["page"], 5)
                self.assertIn("η Εταιρεία οργανώνεται", results[0]["text"])

    def test_headquarters_answer_remains_in_top_three(self):
        for question in ["Ποια είναι η έδρα της εταιρείας;", "Πού εδρεύει η εταιρεία;"]:
            with self.subTest(question=question):
                results = retrieve(question, self.chunks)
                self.assertTrue(any("Έδρα της εταιρείας ορίζεται ο Δήμος" in r["text"]
                                    for r in results))

    def test_unrelated_question_and_common_words_return_no_matches(self):
        for question in ["Πώς φτιάχνω μακαρόνια;", "αστροναύτες", "της τους", ""]:
            with self.subTest(question=question):
                self.assertEqual(retrieve(question, self.chunks), [])


if __name__ == "__main__":
    unittest.main()
