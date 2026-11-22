# Document Assistant frontend

Angular app using AppModule and a non-standalone root component.

## Run locally

Requires Node.js compatible with Angular 22 (for example 24.15 or later in the 24.x series).

Start the backend from the repository root in a separate terminal:

```bash
source backend/.venv/bin/activate
python -m uvicorn main:app --app-dir backend --reload
```

Keep Ollama running with `llama3.2:3b` installed. Then, in another terminal:

```bash
cd frontend
npm ci
npm start
```

Open http://localhost:4200. The development proxy forwards `/ask` to FastAPI on port 8000.

Choose BM25, Vector, or Hybrid using the search-mode radio buttons before submitting a question. BM25 is selected by default. The selected value is sent as `search_mode` in the API request. The controls are disabled while an answer is loading.

## Build

```bash
npm run build
```

The production output is in `dist/document-assistant/browser`. A production host would also need to forward `/ask` to the backend; the Angular development proxy only runs with `npm start`.

## Main files

- `src/app/app.module.ts`: declares the root component and imports browser/forms support.
- `src/app/app.ts`: form state and submit behavior.
- `src/app/app.html`: question form, answer, and sources.
- `src/app/ask.service.ts`: typed HTTP request to FastAPI.
