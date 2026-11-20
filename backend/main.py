import json

import httpx
from fastapi import FastAPI, HTTPException
from ollama import ResponseError
from pydantic import BaseModel, ConfigDict, Field

from llm_api import ask
from retrieve import CHUNKS_FILE


app = FastAPI(title="Document Assistant")
chunks = json.loads(CHUNKS_FILE.read_text(encoding="utf-8"))


class AskRequest(BaseModel):
    model_config = ConfigDict(str_strip_whitespace=True)
    question: str = Field(min_length=1, max_length=2000)


class Source(BaseModel):
    document: str
    section: str
    page: int


class AskResponse(BaseModel):
    answer: str
    sources: list[Source]


@app.post("/ask", response_model=AskResponse)
def ask_question(request: AskRequest):
    try:
        return ask(request.question, chunks)
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
    except (ValueError, KeyError, TypeError) as error:
        raise HTTPException(
            status_code=502, detail="Ollama returned an invalid answer or source reference."
        ) from error
