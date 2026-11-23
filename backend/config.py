import os


# Compose uses the Ollama service name; direct local runs keep the old default.
OLLAMA_HOST = os.environ.get("OLLAMA_HOST", "http://localhost:11434")
