"""Retrieve the most similar stored repository chunks for an embedding."""

from __future__ import annotations

import argparse
import importlib.util
import json
import math
import re
from pathlib import Path
from typing import Any, Sequence


EXACT_NAME_BOOST = 0.5
NAME_OVERLAP_BOOST = 0.15
PATH_OVERLAP_BOOST = 0.05


def _metadata_tokens(value: str) -> set[str]:
    separated = re.sub(r"([a-z0-9])([A-Z])", r"\1 \2", value)
    return set(re.findall(r"[a-z0-9]+", separated.lower()))


def _validated_vector(vector: Sequence[float], expected_size: int | None = None) -> list[float]:
    if not vector:
        raise ValueError("Embedding vectors must not be empty")
    values = []
    for value in vector:
        if isinstance(value, bool) or not isinstance(value, (int, float)):
            raise ValueError("Embedding values must be numbers")
        number = float(value)
        if not math.isfinite(number):
            raise ValueError("Embedding values must be finite")
        values.append(number)
    if expected_size is not None and len(values) != expected_size:
        raise ValueError(
            f"Embedding dimension mismatch: expected {expected_size}, got {len(values)}"
        )
    return values


def cosine_similarity(left: Sequence[float], right: Sequence[float]) -> float:
    """Return cosine similarity; zero vectors have similarity zero."""
    left_values = _validated_vector(left)
    right_values = _validated_vector(right, len(left_values))
    left_norm = math.sqrt(sum(value * value for value in left_values))
    right_norm = math.sqrt(sum(value * value for value in right_values))
    if left_norm == 0.0 or right_norm == 0.0:
        return 0.0
    return sum(a * b for a, b in zip(left_values, right_values)) / (
        left_norm * right_norm
    )


def choose_chunks(
    query_embedding: Sequence[float],
    embedding_storage: dict[str, Any],
    n: int,
    query_text: str | None = None,
) -> list[dict[str, Any]]:
    """Return up to n chunks ranked by cosine plus optional metadata relevance."""
    if n < 0:
        raise ValueError("n must not be negative")
    dimension = embedding_storage.get("dimensions")
    query = _validated_vector(query_embedding, dimension)
    records = embedding_storage.get("embeddings")
    if not isinstance(records, list):
        raise ValueError("Embedding storage must contain an 'embeddings' list")
    query_tokens = _metadata_tokens(query_text) if query_text else set()

    ranked = []
    for index, record in enumerate(records):
        if not isinstance(record, dict):
            raise ValueError(f"Embedding record {index} must be an object")
        if not isinstance(record.get("id"), str):
            raise ValueError(f"Embedding record {index} must have a string 'id'")
        vector = _validated_vector(record.get("embedding", []), len(query))
        name = record.get("name")
        path = record.get("path")
        name_tokens = _metadata_tokens(name) if isinstance(name, str) else set()
        path_tokens = _metadata_tokens(path) if isinstance(path, str) else set()
        name_overlap = len(query_tokens & name_tokens) / len(name_tokens) if name_tokens else 0
        path_overlap = len(query_tokens & path_tokens) / len(path_tokens) if path_tokens else 0
        metadata_boost = NAME_OVERLAP_BOOST * name_overlap
        if name_tokens and name_tokens <= query_tokens:
            metadata_boost += EXACT_NAME_BOOST
        metadata_boost += PATH_OVERLAP_BOOST * path_overlap
        similarity = cosine_similarity(query, vector)
        ranked.append(
            {
                "id": record["id"],
                "path": path,
                "kind": record.get("kind"),
                "name": name,
                "similarity": similarity,
                "score": similarity + metadata_boost,
            }
        )
    ranked.sort(key=lambda result: result["score"], reverse=True)
    return ranked[:n]


def _load_embedder():
    script = Path(__file__).resolve().parents[1] / "Task_3" / "embeder.py"
    spec = importlib.util.spec_from_file_location("task3_embeder", script)
    if spec is None or spec.loader is None:
        raise ImportError(f"Could not load embedding script: {script}")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def main() -> None:
    task_directory = Path(__file__).resolve().parent
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("query", help="text describing the coding task")
    parser.add_argument("-n", type=int, default=5, help="number of chunks to return")
    parser.add_argument(
        "--embeddings",
        type=Path,
        default=task_directory.parent / "Task_3" / "embeddings.json",
        help="embedding storage JSON",
    )
    parser.add_argument(
        "--chunks",
        type=Path,
        default=task_directory.parent / "Task_2" / "structure.json",
        help="chunk structure JSON, used to include retrieved source text",
    )
    args = parser.parse_args()
    if args.n < 0:
        parser.error("-n must not be negative")

    with args.embeddings.open(encoding="utf-8") as file:
        storage = json.load(file)
    embedder = _load_embedder()
    query_embedding = embedder.embed_text(
        args.query,
        storage["idf"],
        storage["document_count"],
        storage["dimensions"],
    )
    results = choose_chunks(query_embedding, storage, args.n, query_text=args.query)

    with args.chunks.open(encoding="utf-8") as file:
        chunks = json.load(file)["chunks"]
    chunks_by_id = {chunk["id"]: chunk for chunk in chunks}
    for result in results:
        chunk = chunks_by_id.get(result["id"])
        if chunk is not None:
            result["text"] = chunk["text"]
    print(json.dumps(results, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()