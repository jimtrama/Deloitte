import json
import re
from pathlib import Path

from pypdf import PdfReader


BASE_DIR = Path(__file__).resolve().parent
DOCS_DIR = BASE_DIR / "docs"
OUTPUT_FILE = BASE_DIR / "data" / "chunks.json"


def read_document(path):
    """Return text sections with source metadata."""

    if path.suffix.lower() == ".pdf":
        reader = PdfReader(path)

        for page_number, page in enumerate(reader.pages, start=1):
            text = page.extract_text() or ""
            print(f"Page {page_number}: {text[:300]}")

            if text.strip():
                yield {
                    "document": path.name,
                    "section": f"Page {page_number}",
                    "page": page_number,
                    "text": text,
                }
            else:
                print(f"Warning: no text in {path.name}, page {page_number}")


def split_into_chunks(text, chunk_size=200):
    """Group paragraphs into chunks without exceeding the word limit."""
    if chunk_size <= 0:
        raise ValueError("chunk_size must be greater than zero")

    # Paragraphs are separated by one or more blank lines.
    paragraphs = re.split(r"\n\s*\n", text.strip())

    current = []
    current_words = 0

    for paragraph in paragraphs:
        paragraph = paragraph.strip()
        words = paragraph.split()

        if not words:
            continue

        # Split unusually long paragraphs by word count.
        if len(words) > chunk_size:
            if current:
                yield "\n\n".join(current)
                current = []
                current_words = 0

            for start in range(0, len(words), chunk_size):
                yield " ".join(words[start:start + chunk_size])

            continue

        # Save the current chunk if this paragraph would exceed the limit.
        if current_words + len(words) > chunk_size:
            yield "\n\n".join(current)
            current = []
            current_words = 0

        current.append(paragraph)
        current_words += len(words)

    if current:
        yield "\n\n".join(current)


def ingest():
    chunks = []

    for path in sorted(DOCS_DIR.iterdir()):
        if not path.is_file():
            continue

        if path.suffix.lower() not in {".pdf", ".md", ".txt"}:
            continue

        for section in read_document(path):
            for text in split_into_chunks(section["text"]):
                chunks.append({
                    "id": f"chunk-{len(chunks) + 1}",
                    "document": section["document"],
                    "section": section["section"],
                    "page": section["page"],
                    "text": text,
                })

    OUTPUT_FILE.parent.mkdir(parents=True, exist_ok=True)
    OUTPUT_FILE.write_text(
        json.dumps(chunks, indent=2, ensure_ascii=False),
        encoding="utf-8",
    )

    print(f"Saved {len(chunks)} chunks to {OUTPUT_FILE}")


if __name__ == "__main__":
    ingest()