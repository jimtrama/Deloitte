# Document Assistant

A local document question-answering app built with Python, FastAPI and Angular. It retrieves passages from the included Greek PDFs, asks Ollama to answer from those passages, and displays the answer with document names and PDF page numbers.

BM25 is the default search mode. The UI also provides radio buttons for vector and hybrid search. No paid LLM API key is required.

## 1. How to run it and the tests

### Run the whole app with Docker

Install and start Docker Desktop (or Docker Engine with the Compose plugin), then run from the repository root:

```bash
docker compose up --build
```

Open [the containerized app](http://localhost:8080) or [its API docs](http://localhost:8080/docs). This setup does not require Python, Node.js or a separate Ollama installation on the host.

The [multi-stage Dockerfile](Dockerfile) builds the production Angular bundle and a FastAPI runtime. [Compose](compose.yaml) starts Ollama, downloads `llama3.2:3b` and `embeddinggemma`, runs ingestion and embedding preparation, then starts FastAPI and Nginx in dependency order. The `models` and `prepare-data` services are one-time setup jobs; an exit code of 0 is expected. Nginx serves the UI and forwards `/ask`, `/docs`, `/openapi.json` and `/health` to the backend.

The first startup downloads several gigabytes of images/models and prepares the index, so it can take several minutes. Follow progress with:

```bash
docker compose logs -f models prepare-data backend
```

Named volumes preserve downloaded models and generated chunks/embeddings. Stop the stack with `docker compose down`; that command keeps those volumes. Host-generated `embeddings.json`, virtual environments, dependencies and `.env` files are excluded from the build context. The default Docker setup uses CPU inference and does not share the native Ollama model cache or configure GPU acceleration.

After changing code or PDFs, rebuild and rerun preparation:

```bash
docker compose down
docker compose up --build
```

To run the backend tests in a container without starting Ollama or the other services:

```bash
docker compose build backend
docker compose run --rm --no-deps backend python -m unittest discover -s backend/tests -t backend -p 'test_*.py' -v
```

`OLLAMA_HOST` controls the backend's model connection. Compose sets it to `http://ollama:11434`; direct local runs default to `http://localhost:11434`. The API's `/health` endpoint checks the application process without invoking a model. Only the Nginx port is published, on `127.0.0.1:8080`.

### Prerequisites for running without Docker

- Python 3.9 or later and `venv`.
- Node.js compatible with Angular 22; this project was built with Node.js 24.15.0.
- npm.
- Ollama installed and running locally at `http://localhost:11434`.

The shell commands below are for macOS/Linux. Run them from the cloned repository root unless a command changes the directory.

### Backend setup

```bash
python3 -m venv backend/.venv
source backend/.venv/bin/activate
python -m pip install -r backend/requirements.txt
ollama pull llama3.2:3b
python backend/ingest.py
```

Ingestion reads PDFs from `backend/docs/` and writes `backend/data/chunks.json`. The current corpus produces 278 chunks. A virtual environment is local to the checkout; recreate it rather than copying one from another machine or folder.

Start the API:

```bash
python -m uvicorn main:app --app-dir backend --reload
```

Open [the interactive API docs](http://127.0.0.1:8000/docs). `POST /ask` accepts a question and an optional search mode:

```json
{
  "question": "Ποια είναι η έδρα της εταιρείας;",
  "search_mode": "bm25"
}
```

Allowed modes are `bm25`, `vector` and `hybrid`; omitting the field uses `bm25`. The response contains `answer` and `sources`, where each source has `document`, `section` and `page`. Page numbers refer to physical PDF pages, which can differ from printed numbering.

### Optional vector and hybrid search setup

With Ollama running, use another terminal with the virtual environment activated:

```bash
ollama pull embeddinggemma
python backend/vector_search.py
```

This embeds the chunks and creates `backend/data/embeddings.json`, a generated local index ignored by Git. Rebuild it after changing the chunks or embedding model, then restart FastAPI. Hybrid mode logs a warning and falls back to BM25 if its vector index/model is unavailable. Explicit vector-only mode reports a setup error instead.

### Frontend

Keep FastAPI and Ollama running. In a separate terminal:

```bash
cd frontend
npm start
```

Open [the app](http://localhost:4200). Enter a question, choose BM25, Vector or Hybrid, and submit it. BM25 is selected initially. The development proxy forwards `/ask` to FastAPI on port 8000. The form includes labels, keyboard-accessible controls, loading/error feedback and an answer/source list.


### Automated tests

From the repository root, with the Python virtual environment activated:

```bash
python -m unittest discover -s backend/tests -t backend -p 'test_*.py' -v
```

The suite currently contains 33 tests covering API validation, response/source handling, Greek normalization, retrieval regressions, vector scoring, index invalidation, hybrid fallback and Ollama host configuration. Ollama and the FastAPI server do not need to be running: external calls are mocked where needed. Corpus regression tests use the saved `backend/data/chunks.json`; regenerate it first if it is missing. The `-t backend` option keeps application modules importable during discovery.

To run only retrieval tests:

```bash
python -m unittest discover -s backend/tests -t backend -p 'test_retrieve.py' -v
```

### GitHub Actions

[The backend test workflow](.github/workflows/backend-tests.yml) runs automatically on pushes and pull requests. It can also be started manually from the repository's **Actions** tab once the workflow is on the default branch.

The workflow runs on an Ubuntu runner, installs Python 3.12 and the backend requirements, then executes the same `unittest` discovery command shown above. The pip download cache is keyed by `backend/requirements.txt`. Ollama, model downloads, an embedding index and API secrets are not required for this test suite. The checked-in `backend/data/chunks.json` supplies the corpus regression data.

To activate it, commit and push the workflow to GitHub. Open **Actions > Backend tests**, select a run and expand **Run backend tests** to inspect the results. A failed test makes the job fail. The workflow checks backend tests; it does not run the live model evaluation or build the frontend.

For a separate live retrieval comparison, Ollama, EmbeddingGemma and an up-to-date embedding index are required:

```bash
python backend/evaluate_search.py
```

This updates `backend/data/search_evaluation.json`. To inspect retrieved passages without generating an answer:

```bash
python backend/hybrid_search.py "Ποτε ιδρύθηκε η εταιρεια ;" --mode bm25
```

## 2. Decisions and improvements with more time

### Design decisions

| Decision | Reason and tradeoff |
| --- | --- |
| Python and FastAPI | Follow the preferred backend stack and provide a small typed JSON API with request validation and interactive documentation. |
| Angular with `AppModule` | Use the requested non-standalone structure, with view state in the component and HTTP calls in a service. |
| Plain Python functions for RAG orchestration | Keep ingestion, retrieval and generation explicit and easy to debug, without adding a RAG framework to this small application. |
| Page-based ingestion with metadata | Preserve document/page provenance so retrieved passages can be traced back to the original PDFs. |
| Paragraph/sentence-aware chunks capped at 200 words | Keep passages manageable while avoiding arbitrary cuts where possible. This is a word limit, not a token limit. Long sentences still require a word-count fallback. |
| Lists instead of generators | Favor readability for the small corpus; ingestion functions collect results and return lists. |
| BM25 as the default | Provide an inspectable keyword baseline that was stronger than vector-only search on the development questions. Greek accent normalization, stemming and small explicit related-word groups improve matching. |
| Optional local embeddings | Explore semantic retrieval through the existing Ollama setup. The current EmbeddingGemma index contains 768-dimensional vectors; that dimension comes from the model rather than a manually selected search setting. |
| In-memory cosine search | The small corpus does not require a separate vector database. Saved vectors are checked against a corpus fingerprint and model digest before use. |
| Weighted reciprocal rank fusion | Combine ranking positions rather than incompatible raw BM25/cosine scores. Initial settings favor BM25: keyword weight 0.7, vector weight 0.3, rank constant 1. |
| Local `llama3.2:3b` for answers | Avoid a paid API dependency and keep inference local. The tradeoff is limited Greek answer quality on these documents. |
| Structured model output and source-number checks | Restrict citations to supplied passage numbers, then attach document/page metadata on the server. These checks validate reference structure, not whether the evidence supports every claim. |
| Docker Compose with separate services | Package the built Angular UI, API and local model server independently. Setup jobs prepare models/data before the app starts; named volumes preserve derived data and model downloads. |

The application flow is:

```text
PDFs -> chunks with metadata -> retrieval -> selected passages
     -> Ollama answer and passage references -> API -> Angular UI
```

Ingestion and document embedding run during preparation. At question time, BM25 searches the saved chunks; vector search additionally embeds the question. The application does not fine-tune either model on the documents.

### Evaluation and current limitations

The saved development report compares all modes on the same eight answerable cases and three negative cases, using the top three passages:

| Method | Cases with the selected supporting passage retrieved | Negative cases rejected |
| --- | --- | --- |
| BM25 | 6/8 | 2/3 |
| Vector | 4/8 | 3/3 |
| Hybrid | 6/8 | 3/3 |

These results measure retrieval, not generated-answer correctness. The set is small, includes wording variants, and was also used to choose settings; it is not an independent benchmark. An organization paraphrase and an English headquarters question failed under all modes. Hybrid remains optional because it did not improve the answerable-case total.

The hybrid similarity threshold of 0.45 is a query-level heuristic, not a correctness probability. A successful low-similarity rejection returns no passages; an index/model failure instead triggers the logged BM25 fallback. The small answer model can still select irrelevant text or attach imperfect citations even when retrieval includes the correct passage. Temperature zero and valid source numbers do not eliminate that risk.

With more time, I would prioritize:

1. **Document scope and extraction:** the three current PDFs total 112 pages, exceeding the assessment's 5-30-page guidance. Select suitable excerpts or smaller public documents, preserve their provenance, and rebuild/retest. Clean OCR errors and repeated headers.
2. **Chunk context:** add dedicated ingestion tests, keep legal headings with their explanations, handle abbreviations, and evaluate article-aware chunks, overlap or neighboring passages across page boundaries.
3. **Answer faithfulness:** evaluate whether answers actually address the question and are supported by their cited passages; validate claimed quotations against source text. Compare a stronger multilingual answer model if resources allow.
4. **Broader evaluation:** add more labeled questions, paraphrases and negative cases, then reserve a held-out set before tuning thresholds, weights or model choices.
5. **Efficiency and delivery:** cache BM25 statistics and a validated vector index, manage inference concurrency, add frontend tests/build checks to CI, and document production routing. Authentication, rate limiting and deployment controls would be needed before offering this as a public service.

## 3. Five example questions and observed answers

The following are actual `POST /ask` responses captured on **22 November 2026**, using `search_mode: "bm25"`, the local `llama3.2:3b` model and temperature `0`. The answer wording and returned source references are reproduced without rewriting. Outputs can vary with model/runtime changes; these examples are observations, not guarantees or manually corrected reference answers.

### 1. Registered office

**Question:** Ποια είναι η έδρα της εταιρείας;

```json
{
  "answer": "Έδρα της εταιρείας ορίζεται ο Δήμος Θεσσαλονίκης της Περιφερειακής Ενότητας Θεσσαλονίκης.",
  "sources": [
    {
      "document": "2024_Καταστατικό-ΑΖΚ.pdf",
      "section": "Page 3",
      "page": 3
    }
  ]
}
```

### 2. Company purpose

**Question:** Ποιος είναι ο σκοπός της εταιρείας;

```json
{
  "answer": "Σκοπός της Εταιρείας είναι ο σχεδιασμός, η οργάνωση, η υλοποίηση, η παρακολούθηση, η διοίκηση, η λειτουργία, η εκμετάλλευση και η αξιολόγηση προγραμμάτων, δράσεων και έργων που συμβάλλουν στην επίτευξη του σκοπού της Ζ.ΚΑΙ.Θ., καθώς και στην ανάπτυξη αυτής.",
  "sources": [
    {
      "document": "2024_Καταστατικό-ΑΖΚ.pdf",
      "section": "Page 4",
      "page": 4
    },
    {
      "document": "2024_Καταστατικό-ΑΖΚ.pdf",
      "section": "Page 3",
      "page": 3
    }
  ]
}
```

### 3. Company duration

**Question:** Ποια είναι η διάρκεια της εταιρείας;

```json
{
  "answer": "Η διάρκεια της Εταιρείας ορίζεται σε πενήντα (50) έτη και αρχίζει από την σχετική καταχώρηση στο Μητρώο Ανωνύμων Εταιρειών από την αρμόδια εποπτεύουσα αρχή.",
  "sources": [
    {
      "document": "2024_Καταστατικό-ΑΖΚ.pdf",
      "section": "Page 6",
      "page": 6
    }
  ]
}
```

### 4. Establishment

**Question:** Ποτε ιδρύθηκε η εταιρεια ;

```json
{
  "answer": "Η εταιρεία συστάθηκε με το ν.3489/2006 (Α΄ 205), όπως τροποποιήθηκε και ισχύει, συστάθηκε η ανώνυμη εταιρεία με την επωνυμία «Αλεξάνδρεια Ζώνη Καινοτομίας Α.Ε.» («Εταιρεία») και λειτουργεί σύμφωνα με τις διατάξεις του N.3489/2006 και του Καταστατικού της (YA Αριθμ. 2606/2014)",
  "sources": [
    {
      "document": "2024_Καταστατικό-ΑΖΚ.pdf",
      "section": "Page 2",
      "page": 2
    },
    {
      "document": "kanonismos_fixed.pdf",
      "section": "Page 4",
      "page": 4
    }
  ]
}
```

### 5. Outside the documents

**Question:** Πώς φτιάχνω μακαρόνια;

```json
{
  "answer": "The documents do not contain the information needed to answer this question.",
  "sources": []
}
```

The fourth answer contains repetition and additional regulatory details; it is retained as returned to show the current model limitation. In the fifth case, retrieval found no relevant passages and the system returned the no-information response with no sources. A response with valid source fields still needs checking against the cited document text.

## 4. AI assistance

OpenAI Codex was used during development for:

- Implementing and debugging BM25, Greek preprocessing, vector search, index validation, hybrid fusion and retrieval evaluation.
- Building the FastAPI endpoint, response/source validation and error handling.
- Creating the NgModule-based Angular UI, HTTP service, accessibility/loading states and search-mode radio buttons.
- Adding Docker/Compose configuration, Nginx API routing, application health checks and a configurable Ollama connection address.
- Writing and reorganizing automated tests, adding the GitHub Actions test workflow, investigating regressions, running checks and capturing the example outputs above.
- Drafting setup instructions, design explanations, this README and the interview study guide.


