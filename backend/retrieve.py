import json
import re
import unicodedata
from pathlib import Path


CHUNKS_FILE = Path(__file__).resolve().parent / "data" / "chunks.json"
STOP_WORDS = {
    "ο", "η", "το", "οι", "τα", "του", "της", "των", "τον", "την",
    "τις", "τους", "και", "σε", "στο", "στη", "στην", "στον", "με",
    "για", "απο", "να", "ειναι", "τι", "ποιος", "ποια", "ποιο", "που",
    "the", "a", "an", "is", "are", "of", "to", "in", "and", "what",
}


def tokenize(text):
    """Extract unique words, ignoring capitalization and accents."""
    normalized = unicodedata.normalize("NFD", text.casefold())
    normalized = "".join(
        character for character in normalized
        if not unicodedata.combining(character)
    )
    words = re.findall(r"[^\W_]+", normalized)
    return set(words) - STOP_WORDS


def retrieve(question, chunks, top_k=3):
    """Return chunks sharing the most distinct keywords with the question."""
    if top_k <= 0:
        raise ValueError("top_k must be greater than zero")

    question_words = tokenize(question)
    results = []

    for chunk in chunks:
        chunk_words = tokenize(chunk["text"])
        score = len(question_words & chunk_words)

        if score > 0:
            results.append({**chunk, "score": score})

    results.sort(key=lambda result: result["score"], reverse=True)
    return results[:top_k]


if __name__ == "__main__":
    question = "Ποια είναι η έδρα της εταιρείας;"

    chunks = json.loads(CHUNKS_FILE.read_text(encoding="utf-8"))
    results = retrieve(question, chunks)

    if not results:
        print("No matching chunks found.")

    for result in results:
        print(f"\n{result['document']} | {result['section']} | Score: {result['score']}")
        print(result["text"])
        print("-" * 80)
