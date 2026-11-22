"""Local semantic search. Run this file after ingestion to build the index."""

import hashlib
import json
import math
from pathlib import Path

from ollama import Client

from retrieve import CHUNKS_FILE


MODEL = "embeddinggemma"
INDEX_FILE = Path(__file__).resolve().parent / "data" / "embeddings.json"
INDEX_VERSION = 1
# This is a retrieval filter, not a probability that an answer is correct.
MIN_SIMILARITY = 0.45


class EmbeddingIndexError(ValueError):
    """The local index/model needs setup or rebuilding."""


def fingerprint(chunks):
    content = json.dumps(chunks, ensure_ascii=False, sort_keys=True)
    return hashlib.sha256(content.encode("utf-8")).hexdigest()


def unit_vector(vector):
    if not vector or any(not isinstance(x, (float, int)) or not math.isfinite(x)
                         for x in vector):
        raise ValueError("Invalid embedding vector")
    length = math.sqrt(sum(x * x for x in vector))
    if not length:
        raise ValueError("Embedding vector must not be zero")
    return [x / length for x in vector]


def model_digest(client):
    for model in client.list().models:
        if model.model in {MODEL, MODEL + ":latest"}:
            return model.digest
    raise EmbeddingIndexError(f"Run ollama pull {MODEL} before building the index")


def build_index(chunks, path=INDEX_FILE, batch_size=16):
    if not chunks or batch_size <= 0:
        raise ValueError("Provide chunks and a positive batch size")
    client = Client(host="http://localhost:11434", timeout=120)
    digest = model_digest(client)
    vectors = []
    for start in range(0, len(chunks), batch_size):
        batch = chunks[start:start + batch_size]
        response = client.embed(
            model=MODEL,
            input=[f"title: none | text: {chunk['text']}" for chunk in batch],
            truncate=False,
        )
        if len(response.embeddings) != len(batch):
            raise ValueError("Ollama returned an incorrect number of embeddings")
        vectors.extend(unit_vector(vector) for vector in response.embeddings)
        print(f"Embedded {len(vectors)}/{len(chunks)} chunks", flush=True)

    dimension = len(vectors[0])
    if any(len(vector) != dimension for vector in vectors):
        raise ValueError("Embedding dimensions do not match")
    index = {
        "version": INDEX_VERSION, "model": MODEL, "model_digest": digest,
        "fingerprint": fingerprint(chunks), "dimension": dimension, "vectors": vectors,
    }
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_suffix(".tmp")
    temporary.write_text(json.dumps(index), encoding="utf-8")
    temporary.replace(path)
    return index


def load_index(chunks, path=INDEX_FILE):
    try:
        index = json.loads(Path(path).read_text(encoding="utf-8"))
        if (index.get("version") != INDEX_VERSION or index.get("model") != MODEL
                or index.get("fingerprint") != fingerprint(chunks)):
            raise EmbeddingIndexError("Embedding index is outdated; rebuild it")
        vectors = index["vectors"]
        if len(vectors) != len(chunks) or any(len(v) != index["dimension"] for v in vectors):
            raise EmbeddingIndexError("Embedding index dimensions do not match the chunks")
    except (OSError, ValueError, KeyError, TypeError, AttributeError) as error:
        raise EmbeddingIndexError("Run python backend/vector_search.py to rebuild the index") from error
    return index


def rank_vectors(chunks, vectors, question_vector, top_k=20, min_similarity=MIN_SIMILARITY):
    if top_k <= 0 or len(chunks) != len(vectors):
        raise ValueError("Invalid result limit or vector count")
    question_vector = unit_vector(question_vector)
    results = []
    for chunk, vector in zip(chunks, vectors):
        if len(vector) != len(question_vector):
            raise ValueError("Query and document embedding dimensions differ")
        vector = unit_vector(vector)
        similarity = sum(a * b for a, b in zip(question_vector, vector))
        if similarity >= min_similarity:
            results.append({**chunk, "score": similarity, "similarity": similarity})
    results.sort(key=lambda result: result["score"], reverse=True)
    return results[:top_k]


def vector_retrieve(question, chunks, top_k=20, min_similarity=MIN_SIMILARITY):
    if top_k <= 0:
        raise ValueError("top_k must be greater than zero")
    if not question.strip() or not chunks:
        return []
    index = load_index(chunks)
    client = Client(host="http://localhost:11434", timeout=120)
    if model_digest(client) != index["model_digest"]:
        raise EmbeddingIndexError("Embedding model changed; rebuild the embedding index")
    response = client.embed(
        model=MODEL, input=f"task: search result | query: {question}", truncate=False,
    )
    results = rank_vectors(chunks, index["vectors"], response.embeddings[0], top_k,
                           min_similarity=-1)
    # Gate the question as a whole; do not discard lower-scoring supporting passages.
    if not results or results[0]["similarity"] < min_similarity:
        return []
    return results


if __name__ == "__main__":
    chunks = json.loads(CHUNKS_FILE.read_text(encoding="utf-8"))
    build_index(chunks)
    print(f"Saved embedding index to {INDEX_FILE}")
