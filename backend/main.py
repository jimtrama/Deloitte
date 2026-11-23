import json
from typing import Literal

import httpx
from fastapi import FastAPI, HTTPException
from ollama import ResponseError
from pydantic import BaseModel, ConfigDict, Field

from llm_api import ask
from retrieve import CHUNKS_FILE
from vector_search import EmbeddingIndexError


app = FastAPI(title="Document Assistant")
chunks = json.loads(CHUNKS_FILE.read_text(encoding="utf-8"))


class AskRequest(BaseModel):
    model_config = ConfigDict(str_strip_whitespace=True)
    question: str = Field(min_length=1, max_length=2000)
    search_mode: Literal["bm25", "vector", "hybrid"] = "bm25"


class Source(BaseModel):
    document: str
    section: str
    page: int


class AskResponse(BaseModel):
    answer: str
    sources: list[Source]


@app.get("/health")
def health():
    """Check API readiness without invoking either model."""
    return {"status": "ok"}


@app.post("/ask", response_model=AskResponse)
def ask_question(request: AskRequest):
    try:
        return ask(request.question, chunks, search_mode=request.search_mode)
    except (ConnectionError, httpx.ConnectError) as error:
        raise HTTPException(
            status_code=503, detail="Cannot connect to Ollama. Make sure it is running."
        ) from error
    except httpx.TimeoutException as error:
        raise HTTPException(status_code=504, detail="Ollama took too long to respond.") from error
    except ResponseError as error:
        raise HTTPException(
            status_code=502, detail="Ollama failed to answer. Check that llama3.2:3b is installed."
        ) from error
    except EmbeddingIndexError as error:
        raise HTTPException(
            status_code=503, detail="Embedding index unavailable. Run python backend/vector_search.py."
        ) from error
    except (ValueError, KeyError, TypeError) as error:
        raise HTTPException(
            status_code=502, detail="Ollama returned an invalid answer or source reference."
        ) from error
