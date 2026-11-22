"""Small retrieval regression set, not a benchmark of answer accuracy."""

import json
from pathlib import Path

from hybrid_search import KEYWORD_WEIGHT, RANK_CONSTANT, fuse_rankings
from retrieve import CHUNKS_FILE, retrieve as bm25_retrieve
from vector_search import MIN_SIMILARITY, MODEL, fingerprint, vector_retrieve


CASES = [
    ("Ποτε ιδρύθηκε η εταιρεια ;", "συστάθηκε η"),
    ("Πότε ιδρύθηκε η εταιρεία;", "συστάθηκε η"),
    ("Ποια ειναι η οργανωση της εταιρειας;", "η Εταιρεία οργανώνεται"),
    ("Πώς είναι διαρθρωμένη η εταιρεία;", "η Εταιρεία οργανώνεται"),
    ("Ποια είναι η έδρα της εταιρείας;", "Έδρα της εταιρείας ορίζεται ο Δήμος"),
    ("Where is the company headquartered?", "Έδρα της εταιρείας ορίζεται ο Δήμος"),
    ("Ποιος είναι ο σκοπός της εταιρείας;", "Σκοπός της Εταιρείας, σύμφωνα"),
    ("Ποια είναι η διάρκεια της εταιρείας;", "Η διάρκεια της Εταιρείας ορίζεται"),
    ("Πώς φτιάχνω μακαρόνια;", None),
    ("αστροναύτες", None),
    ("Ποιος είναι ο κωδικός WiFi της εταιρείας;", None),
]
REPORT_FILE = Path(__file__).resolve().parent / "data" / "search_evaluation.json"


def evaluate():
    chunks = json.loads(CHUNKS_FILE.read_text(encoding="utf-8"))
    rows = []
    totals = {method: {"answerable_hits": 0, "negative_rejections": 0}
              for method in ["bm25", "vector", "hybrid"]}
    for question, expected in CASES:
        keywords = bm25_retrieve(question, chunks, 20)
        # Keep raw similarities in the report to inspect the rejection threshold.
        raw_vectors = vector_retrieve(question, chunks, 20, min_similarity=-1)
        vectors = raw_vectors if raw_vectors and raw_vectors[0]["similarity"] >= MIN_SIMILARITY else []
        rankings = {"bm25": keywords[:3], "vector": vectors[:3],
                    "hybrid": fuse_rankings(keywords, vectors)}
        row = {"question": question, "expected_text": expected,
               "best_cosine_similarity": raw_vectors[0]["similarity"] if raw_vectors else None,
               "methods": {},
               "keyword_candidates": [{"id": r["id"], "score": r["score"]} for r in keywords],
               "vector_candidates": [{"id": r["id"], "similarity": r["similarity"]}
                                     for r in raw_vectors]}
        for method, results in rankings.items():
            hit = any(expected in r["text"] for r in results) if expected else not results
            totals[method]["answerable_hits" if expected else "negative_rejections"] += int(hit)
            row["methods"][method] = {
                "passed": hit,
                "sources": [{"id": r["id"], "document": r["document"], "page": r["page"]}
                            for r in results],
            }
        rows.append(row)
        print(question, "cosine=", round(row["best_cosine_similarity"], 3),
              {method: result["passed"] for method, result in row["methods"].items()}, flush=True)
    report = {"model": MODEL, "corpus_fingerprint": fingerprint(chunks),
              "min_similarity": MIN_SIMILARITY, "keyword_weight": KEYWORD_WEIGHT,
              "rank_constant": RANK_CONSTANT,
              "answerable_cases": sum(expected is not None for _, expected in CASES),
              "negative_cases": sum(expected is None for _, expected in CASES),
              "totals": totals, "cases": rows}
    REPORT_FILE.write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")
    print(json.dumps(totals, indent=2))
    print(f"Saved report to {REPORT_FILE}")
    return report


if __name__ == "__main__":
    evaluate()
