# Document Assistant backend

Python + FastAPI, with BM25 keyword search and optional local vector/hybrid search before asking Ollama for an answer. No external API key or vector database is required. BM25 remains the default: hybrid preserved the baseline's supporting-passage hits on the development set, but did not resolve the generation model's answer-quality problems.

## Setup

From the repository root:

```bash
python3 -m venv backend/.venv
source backend/.venv/bin/activate
python -m pip install -r backend/requirements.txt
ollama pull llama3.2:3b
ollama pull embeddinggemma
```

Keep Ollama running. Read the PDFs into chunks and build document embeddings:

```bash
python backend/ingest.py
python backend/vector_search.py
```

The generated `backend/data/embeddings.json` stays local and is ignored by Git. Run the embedding step again whenever the chunks or embedding model change, then restart FastAPI. Index validation checks the text, metadata, ordering, model identity and model digest before using stored vectors.

Start the API:

```bash
python -m uvicorn main:app --app-dir backend --reload
```

Open http://127.0.0.1:8000/docs to try `POST /ask`:

```json
{"question": "Ποτε ιδρύθηκε η εταιρεια ;", "search_mode": "hybrid"}
```

The response contains `answer` and `sources` (document, section, PDF page).

`search_mode` accepts `bm25`, `vector`, or `hybrid`. Omitting it preserves BM25 behavior for existing clients. The frontend defaults to BM25 and sends the mode selected using its radio buttons. You can also use the API docs or retrieval CLI to compare modes.

## How hybrid search works

1. BM25 matches keywords after accent normalization and Greek stemming. A small explicit vocabulary connects a few related domain terms.
2. EmbeddingGemma embeds the original text, not the stems. Document embeddings are generated once; question embeddings are generated when searching. Query/document prefixes follow the [model's retrieval instructions](https://huggingface.co/google/embeddinggemma-300m#prompt-instructions).
3. Cosine similarity compares the question vector against every document vector in memory. At this corpus size an approximate index or separate database adds little value.
4. Weighted reciprocal rank fusion combines the top 20 candidates from each search. It uses rank positions rather than adding incomparable BM25 and cosine scores. The initial settings favor BM25: 70% keyword weight, 30% vector weight, rank constant 1.
5. A best-vector-similarity threshold of 0.45 rejects questions with little semantic connection to the corpus. This is a heuristic calibrated on the small development set, not a confidence probability or proof that the documents answer a question. Supporting candidates below that threshold are retained when the question passes the gate.
6. Ollama receives the top three passages and returns an answer and passage references. The server maps those references back to source metadata.

If the vector index is missing, stale, corrupt, or unavailable, the application logs a warning and uses BM25. It never silently applies old embeddings to new chunks. If retrieval returns no candidates, Ollama is not called. If Ollama declines to answer, that is logged separately.

The fallback applies to hybrid mode. Explicit vector-only mode reports an error when its index/model is unavailable rather than presenting keyword results as vector results.

## Inspect retrieval and run tests

```bash
python backend/hybrid_search.py "Ποτε ιδρύθηκε η εταιρεια ;"
python backend/hybrid_search.py "Ποια ειναι η οργανωση της εταιρειας;" --mode vector
python backend/hybrid_search.py "Ποια είναι η έδρα της εταιρείας;" --mode bm25
python -m unittest discover -s backend/tests -t backend -p 'test_*.py' -v
```

Unit/API tests use mocks for live embedding/generation calls and can run without Ollama. The corpus regression tests require the included `data/chunks.json`.

The test files live in `backend/tests/`. The `-t backend` option keeps backend modules importable when discovering tests in that subfolder.

For a live comparison using the same questions and top-three cutoff for all methods:

```bash
python backend/evaluate_search.py
```

This saves `data/search_evaluation.json`, including model/settings, corpus fingerprint, per-question results, and candidate rankings. The eight answerable cases test founding, organization, headquarters (including English), purpose and duration; three negative cases test unrelated or unavailable information. Results measure whether a selected supporting passage was retrieved, not whether the generated answer is correct. This development set also helped choose the fusion settings and threshold; it is not an independent benchmark.

Initial results: BM25 found the selected supporting passage in 6/8 answerable cases and rejected 2/3 negatives. Vector-only found 4/8 and rejected 3/3. Hybrid found 6/8 and rejected 3/3. The organization paraphrase and English headquarters question failed in all three modes. Live generation tests also selected irrelevant sentences despite retrieving supporting passages. These results justify keeping hybrid optional pending broader validation and generation improvements.

## Limitations and future improvements

- Greek OCR corruption and text split across chunk boundaries still affect both search methods.
- EmbeddingGemma did not improve every paraphrase or cross-language question in the development set. Preserve the BM25 baseline and evaluate additional labeled questions before changing the model or settings.
- Source numbers are validated structurally; the small generation model can still misinterpret passages or attach an imperfect citation. Retrieval evaluation does not establish answer correctness.
- A threshold cannot reliably distinguish all out-of-scope questions from questions answerable in the documents. Additional negative examples and held-out validation are needed.
- Broader evaluation, cleaner document extraction, neighboring-passage context, and a stronger multilingual embedding/answer model are possible next improvements.

## AI assistance

OpenAI Codex assisted with ingestion/chunking changes, retrieval and embeddings, API/UI implementation, debugging, tests, and documentation. The candidate should review and understand these parts before submission.
