"""Create deterministic feature-hashed TF-IDF embeddings for repository chunks."""

from __future__ import annotations

import argparse
import hashlib
import json
import math
import re
from collections import Counter
from pathlib import Path
from typing import Any


DEFAULT_DIMENSIONS = 512
TOKEN_PATTERN = re.compile(r"[A-Za-z]+|[0-9]+")


def terms(text: str) -> list[str]:
    """Extract lowercase words and identifiers, including underscore parts."""
    text = re.sub(r"([a-z0-9])([A-Z])", r"\1 \2", text)
    tokens = [match.group(0).lower() for match in TOKEN_PATTERN.finditer(text)]
    return tokens + [f"{left}_{right}" for left, right in zip(tokens, tokens[1:])]


def document_frequencies(texts: list[str]) -> tuple[dict[str, int], int]:
    frequencies: Counter[str] = Counter()
    for text in texts:
        frequencies.update(set(terms(text)))
    return dict(frequencies), len(texts)


def embed_text(
    text: str,
    inverse_document_frequencies: dict[str, float],
    document_count: int,
    dimensions: int = DEFAULT_DIMENSIONS,
) -> list[float]:
    if dimensions < 1:
        raise ValueError("Embedding dimensions must be at least 1")

    vector = [0.0] * dimensions
    counts = Counter(terms(text))
    for term, count in counts.items():
        inverse_document_frequency = inverse_document_frequencies.get(
            term, math.log(1 + document_count) + 1.0
        )
        weight = (1.0 + math.log(count)) * inverse_document_frequency

        digest = hashlib.blake2b(term.encode("utf-8"), digest_size=8).digest()
        hashed = int.from_bytes(digest, byteorder="big")
        index = hashed % dimensions
        sign = 1.0 if hashed & (1 << 63) else -1.0
        vector[index] += sign * weight

    norm = math.sqrt(sum(value * value for value in vector))
    if norm:
        vector = [value / norm for value in vector]
    return vector


def build_embedding_map(
    structure: dict[str, Any], dimensions: int = DEFAULT_DIMENSIONS
) -> dict[str, Any]:
    chunks = structure.get("chunks")
    if not isinstance(chunks, list):
        raise ValueError("Input JSON must contain a 'chunks' list")
    if any(not isinstance(chunk.get("id"), str) for chunk in chunks):
        raise ValueError("Every chunk must have a string 'id'")
    if any(not isinstance(chunk.get("text"), str) for chunk in chunks):
        raise ValueError("Every chunk must have string 'text'")

    frequencies, document_count = document_frequencies(
        [chunk["text"] for chunk in chunks]
    )
    inverse_document_frequencies = {
        term: math.log((1 + document_count) / (1 + frequency)) + 1.0
        for term, frequency in frequencies.items()
    }
    records = []
    for chunk in chunks:
        records.append(
            {
                "id": chunk["id"],
                "path": chunk.get("path"),
                "kind": chunk.get("kind"),
                "name": chunk.get("name"),
                "embedding": embed_text(
                    chunk["text"],
                    inverse_document_frequencies,
                    document_count,
                    dimensions,
                ),
            }
        )

    return {
        "source": structure.get("source"),
        "embedding_method": "signed feature-hashed TF-IDF",
        "dimensions": dimensions,
        "document_count": document_count,
        "idf": dict(sorted(inverse_document_frequencies.items())),
        "embeddings": records,
    }


def retrieve(
    query: str, embedding_map: dict[str, Any], top_k: int
) -> list[dict[str, Any]]:
    if top_k < 1:
        raise ValueError("--top-k must be at least 1")
    idf = embedding_map["idf"]
    document_count = embedding_map["document_count"]
    dimensions = embedding_map["dimensions"]
    query_vector = embed_text(query, idf, document_count, dimensions)
    ranked = []
    for record in embedding_map["embeddings"]:
        score = sum(
            query_value * chunk_value
            for query_value, chunk_value in zip(query_vector, record["embedding"])
        )
        ranked.append(
            {
                "id": record["id"],
                "path": record["path"],
                "name": record["name"],
                "similarity": score,
            }
        )
    return sorted(ranked, key=lambda result: result["similarity"], reverse=True)[
        :top_k
    ]


def main() -> None:
    task_directory = Path(__file__).resolve().parent
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--input",
        type=Path,
        default=task_directory.parent / "Task_2" / "structure.json",
        help="chunk JSON input (default: Task_2/structure.json)",
    )
    parser.add_argument(
        "--output",
        type=Path,
        default=task_directory / "embeddings.json",
        help="embedding map output (default: embeddings.json)",
    )
    parser.add_argument("--dimensions", type=int, default=DEFAULT_DIMENSIONS)
    parser.add_argument("--query", help="optionally retrieve the closest chunks")
    parser.add_argument("--top-k", type=int, default=5)
    args = parser.parse_args()

    if args.dimensions < 1:
        parser.error("--dimensions must be at least 1")
    if args.query is not None and args.top_k < 1:
        parser.error("--top-k must be at least 1")

    with args.input.open(encoding="utf-8") as input_file:
        structure = json.load(input_file)
    embedding_map = build_embedding_map(structure, args.dimensions)

    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(
        json.dumps(embedding_map, ensure_ascii=False, separators=(",", ":")) + "\n",
        encoding="utf-8",
    )
    print(f"Wrote {len(embedding_map['embeddings'])} embeddings to {args.output}")

    if args.query is not None:
        for result in retrieve(args.query, embedding_map, args.top_k):
            print(
                f"{result['similarity']:.4f}\t{result['id']}\t"
                f"{result['path']}\t{result['name']}"
            )


if __name__ == "__main__":
    main()