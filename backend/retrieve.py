import json
import math
import re
import unicodedata
from collections import Counter
from pathlib import Path


CHUNKS_FILE = Path(__file__).resolve().parent / "data" / "chunks.json"
STOP_WORDS = {
    "ο", "η", "το", "οι", "τα", "του", "της", "των", "τον", "την",
    "τις", "τους", "και", "σε", "στο", "στη", "στην", "στον", "με",
    "για", "απο", "να", "ειναι", "τι", "ποιος", "ποια", "ποιο", "που",
    "the", "a", "an", "is", "are", "of", "to", "in", "and", "what",
}


def tokenize(text) -> list[str]:
    """Extract words, ignoring capitalization, accents and common words."""
    normalized = unicodedata.normalize("NFD", text.casefold())
    normalized = "".join(
        character for character in normalized
        if not unicodedata.combining(character)
    )
    words = re.findall(r"[^\W_]+", normalized)
    return [word for word in words if word not in STOP_WORDS]


def retrieve(question, chunks, top_k=3):
    """Rank chunks using BM25 keyword search."""
    if top_k <= 0:
        raise ValueError("top_k must be greater than zero")

    question_words = set(tokenize(question))
    if not question_words or not chunks:
        return []

    word_counts = [Counter(tokenize(chunk["text"])) for chunk in chunks]
    chunk_lengths = [sum(counts.values()) for counts in word_counts]
    average_length = sum(chunk_lengths) / len(chunks)
    if average_length == 0:
        return []

    # Count how many chunks contain each word, counting once per chunk.
    document_frequency = Counter()
    for counts in word_counts:
        document_frequency.update(counts.keys())

    k1 = 1.5  # Limit the benefit of repeating the same word.
    b = 0.75  # Adjust for differences in chunk length.
    results = []

    for chunk, counts, length in zip(chunks, word_counts, chunk_lengths):
        score = 0.0
        for word in question_words:
            frequency = counts[word]
            if frequency == 0:
                continue

            matching_chunks = document_frequency[word]
            rarity = math.log(
                1 + (len(chunks) - matching_chunks + 0.5) / (matching_chunks + 0.5)
            )
            length_adjustment = 1 - b + b * length / average_length
            score += rarity * frequency * (k1 + 1) / (
                frequency + k1 * length_adjustment
            )

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
        print(f"\n{result['document']} | {result['section']} | Score: {result['score']:.2f}")
        print(result["text"])
        print("-" * 80)
