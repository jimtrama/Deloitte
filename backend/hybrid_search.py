"""Combine keyword and semantic rankings without mixing incompatible scores."""

import logging
import argparse
import json

import httpx
from ollama import ResponseError

from retrieve import CHUNKS_FILE, query_terms, retrieve as bm25_retrieve
from vector_search import MIN_SIMILARITY, vector_retrieve


logger = logging.getLogger("uvicorn.error")
# Favor the existing keyword search; calibrated on data/search_evaluation.json.
KEYWORD_WEIGHT = 0.7
RANK_CONSTANT = 1


def fuse_rankings(keyword_results, vector_results, top_k=3):
    """Reciprocal rank fusion after the query-level semantic relevance check."""
    if top_k <= 0:
        raise ValueError("top_k must be greater than zero")
    if not vector_results:
        return []
    candidates = {result["id"]: result for result in keyword_results + vector_results}
    scores = {chunk_id: 0.0 for chunk_id in candidates}
    for ranking, weight in [(keyword_results, KEYWORD_WEIGHT),
                            (vector_results, 1 - KEYWORD_WEIGHT)]:
        seen = set()
        for rank, result in enumerate(ranking, start=1):
            chunk_id = result["id"]
            if chunk_id in candidates and chunk_id not in seen:
                scores[chunk_id] += weight / (RANK_CONSTANT + rank)
                seen.add(chunk_id)
    results = [{**chunk, "score": scores[chunk_id]}
               for chunk_id, chunk in candidates.items()]
    results.sort(key=lambda result: result["score"], reverse=True)
    return results[:top_k]


def retrieve(question, chunks, top_k=3):
    if top_k <= 0:
        raise ValueError("top_k must be greater than zero")
    if not query_terms(question) or not chunks:
        return []
    candidate_count = max(20, top_k)
    keywords = bm25_retrieve(question, chunks, candidate_count)
    try:
        vectors = vector_retrieve(question, chunks, candidate_count, MIN_SIMILARITY)
    except (OSError, ValueError, KeyError, TypeError, ConnectionError,
            httpx.HTTPError, ResponseError) as error:
        logger.warning("Vector search unavailable; using BM25: %s", error)
        return keywords[:top_k]
    return fuse_rankings(keywords, vectors, top_k)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Inspect hybrid retrieval without generating an answer.")
    parser.add_argument("question")
    parser.add_argument("--mode", choices=["bm25", "vector", "hybrid"], default="hybrid")
    args = parser.parse_args()
    chunks = json.loads(CHUNKS_FILE.read_text(encoding="utf-8"))
    search = {"bm25": bm25_retrieve, "vector": vector_retrieve, "hybrid": retrieve}[args.mode]
    results = search(args.question, chunks, top_k=3)
    print(json.dumps(results, ensure_ascii=False, indent=2))
