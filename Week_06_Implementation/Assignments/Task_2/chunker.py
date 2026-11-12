"""Split a repository into JSON chunks aligned to Python symbols."""

from __future__ import annotations

import argparse
import ast
import json
from pathlib import Path
from typing import Any


SKIP_DIRECTORIES = {".git", "__pycache__", ".pytest_cache", ".venv", "venv"}
SYMBOL_NODES = (ast.ClassDef, ast.FunctionDef, ast.AsyncFunctionDef)
MAX_CHUNK_LINES = 100


def repository_files(root: Path):
    """Yield repository files in a stable order, excluding Git and cache data."""
    for path in sorted(root.rglob("*")):
        if not path.is_file():
            continue
        if any(part in SKIP_DIRECTORIES for part in path.relative_to(root).parts):
            continue
        yield path


def _chunk(
    relative_path: str,
    kind: str,
    name: str,
    start_line: int,
    end_line: int,
    text: str,
) -> dict[str, Any]:
    return {
        "path": relative_path,
        "kind": kind,
        "name": name,
        "start_line": start_line,
        "end_line": end_line,
        "text": text,
    }


def _definition_start(node: ast.ClassDef | ast.FunctionDef | ast.AsyncFunctionDef) -> int:
    return min([node.lineno, *(decorator.lineno for decorator in node.decorator_list)])


def _header_and_body(
    node: ast.ClassDef | ast.FunctionDef | ast.AsyncFunctionDef,
    lines: list[str],
    start_line: int,
) -> tuple[str, list[ast.stmt]]:
    body = list(node.body)
    if not body:
        return "".join(lines[start_line - 1 : node.end_lineno]), []

    prefix_end = body[0].lineno - 1
    if (
        isinstance(body[0], ast.Expr)
        and isinstance(body[0].value, ast.Constant)
        and isinstance(body[0].value.value, str)
    ):
        prefix_end = body[0].end_lineno or body[0].lineno
        body.pop(0)
    return "".join(lines[start_line - 1 : prefix_end]), body


def _group_statements(
    statements: list[ast.stmt], prefix_lines: int, max_lines: int
) -> list[list[ast.stmt]]:
    groups: list[list[ast.stmt]] = []
    current: list[ast.stmt] = []
    for statement in statements:
        candidate = [*current, statement]
        candidate_lines = (
            (candidate[-1].end_lineno or candidate[-1].lineno) - candidate[0].lineno + 1
        )
        if current and prefix_lines + candidate_lines > max_lines:
            groups.append(current)
            current = [statement]
        else:
            current = candidate
    if current:
        groups.append(current)
    return groups


def _function_chunks(
    relative_path: str,
    node: ast.FunctionDef | ast.AsyncFunctionDef,
    lines: list[str],
    context: str = "",
    name_prefix: str = "",
) -> list[dict[str, Any]]:
    start_line = _definition_start(node)
    end_line = node.end_lineno or node.lineno
    full_text = "".join(lines[start_line - 1 : end_line])
    if len(full_text.splitlines()) + len(context.splitlines()) <= MAX_CHUNK_LINES:
        return [
            _chunk(
                relative_path,
                "function",
                f"{name_prefix}{node.name}",
                start_line,
                end_line,
                context + full_text,
            )
        ]

    prefix, body = _header_and_body(node, lines, start_line)
    if not body:
        return [
            _chunk(
                relative_path,
                "function",
                f"{name_prefix}{node.name}",
                start_line,
                end_line,
                context + full_text,
            )
        ]

    groups = _group_statements(
        body,
        len(context.splitlines()) + len(prefix.splitlines()),
        MAX_CHUNK_LINES,
    )
    chunks = []
    for part, group in enumerate(groups, start=1):
        body_start = group[0].lineno
        body_end = group[-1].end_lineno or group[-1].lineno
        text = context + prefix + "".join(lines[body_start - 1 : body_end])
        chunks.append(
            _chunk(
                relative_path,
                "function_part",
                f"{name_prefix}{node.name} (part {part})",
                body_start,
                body_end,
                text,
            )
        )
    return chunks


def _class_chunks(
    relative_path: str, node: ast.ClassDef, lines: list[str]
) -> list[dict[str, Any]]:
    start_line = _definition_start(node)
    end_line = node.end_lineno or node.lineno
    full_text = "".join(lines[start_line - 1 : end_line])
    if len(full_text.splitlines()) <= MAX_CHUNK_LINES:
        return [_chunk(relative_path, "class", node.name, start_line, end_line, full_text)]

    prefix, body = _header_and_body(node, lines, start_line)
    if not body:
        return [_chunk(relative_path, "class", node.name, start_line, end_line, full_text)]

    groups: list[list[ast.stmt]] = []
    current: list[ast.stmt] = []
    prefix_lines = len(prefix.splitlines())
    for member in body:
        member_lines = (member.end_lineno or member.lineno) - member.lineno + 1
        if isinstance(member, (ast.FunctionDef, ast.AsyncFunctionDef)) and (
            prefix_lines + member_lines > MAX_CHUNK_LINES
        ):
            if current:
                groups.append(current)
                current = []
            groups.append([member])
        elif current and prefix_lines + (
            (member.end_lineno or member.lineno) - current[0].lineno + 1
        ) > MAX_CHUNK_LINES:
            groups.append(current)
            current = [member]
        else:
            current.append(member)
    if current:
        groups.append(current)

    chunks: list[dict[str, Any]] = []
    part = 1
    for group in groups:
        member = group[0]
        if (
            len(group) == 1
            and isinstance(member, (ast.FunctionDef, ast.AsyncFunctionDef))
            and prefix_lines
            + (member.end_lineno or member.lineno)
            - member.lineno
            + 1
            > MAX_CHUNK_LINES
        ):
            member_chunks = _function_chunks(
                relative_path,
                member,
                lines,
                context=prefix,
                name_prefix=f"{node.name}.",
            )
            chunks.extend(member_chunks)
            part += len(member_chunks)
            continue

        body_start = group[0].lineno
        body_end = group[-1].end_lineno or group[-1].lineno
        chunks.append(
            _chunk(
                relative_path,
                "class_part",
                f"{node.name} (part {part})",
                body_start,
                body_end,
                prefix + "".join(lines[body_start - 1 : body_end]),
            )
        )
        part += 1
    return chunks


def _python_file_chunks(relative_path: str, text: str) -> list[dict[str, Any]]:
    tree = ast.parse(text, filename=relative_path)
    lines = text.splitlines(keepends=True)
    chunks: list[dict[str, Any]] = []
    cursor = 1

    def add_module_chunk(start_line: int, end_line: int) -> None:
        module_text = "".join(lines[start_line - 1 : end_line])
        if module_text.strip():
            chunks.append(
                _chunk(
                    relative_path,
                    "module",
                    f"module:{start_line}-{end_line}",
                    start_line,
                    end_line,
                    module_text,
                )
            )

    for node in tree.body:
        if not isinstance(node, SYMBOL_NODES):
            continue

        start_line = _definition_start(node)
        end_line = node.end_lineno or node.lineno
        if cursor < start_line:
            add_module_chunk(cursor, start_line - 1)

        if isinstance(node, ast.ClassDef):
            chunks.extend(_class_chunks(relative_path, node, lines))
        else:
            chunks.extend(
                _function_chunks(relative_path, node, lines)
            )
        cursor = end_line + 1

    if cursor <= len(lines):
        add_module_chunk(cursor, len(lines))
    if not chunks:
        chunks.append(
            _chunk(
                relative_path,
                "module",
                "module",
                1,
                len(lines),
                text,
            )
        )
    return chunks


def build_chunks(source: Path) -> list[dict[str, Any]]:
    if not source.is_dir():
        raise FileNotFoundError(f"Source repository does not exist: {source}")

    chunks: list[dict[str, Any]] = []
    for path in repository_files(source):
        relative_path = path.relative_to(source).as_posix()
        text = path.read_text(encoding="utf-8")
        if path.suffix == ".py":
            file_chunks = _python_file_chunks(relative_path, text)
        else:
            line_count = len(text.splitlines())
            file_chunks = [
                _chunk(
                    relative_path,
                    "file",
                    path.name,
                    1,
                    line_count,
                    text,
                )
            ]
        chunks.extend(file_chunks)

    for chunk_id, chunk in enumerate(chunks, start=1):
        chunk["id"] = f"chunk-{chunk_id:04d}"
    return chunks


def write_chunks(source: Path, output: Path) -> int:
    chunks = build_chunks(source)
    structure = {
        "source": source.name,
        "chunking_strategy": (
            f"Python chunks target at most {MAX_CHUNK_LINES} lines. Oversized "
            "classes are split at member boundaries; oversized functions are "
            "split at top-level body statement boundaries. Definition headers "
            "are repeated as context. Other text files and Python module-level "
            "code are kept as chunks."
        ),
        "chunk_count": len(chunks),
        "chunks": chunks,
    }
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(
        json.dumps(structure, indent=2, ensure_ascii=False) + "\n",
        encoding="utf-8",
    )
    return len(chunks)


def main() -> None:
    task_directory = Path(__file__).resolve().parent
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--source",
        type=Path,
        default=task_directory.parent / "Task_1" / "cloned_repo",
        help="repository to chunk (default: Task_1/cloned_repo)",
    )
    parser.add_argument(
        "--output",
        type=Path,
        default=task_directory / "structure.json",
        help="JSON file to write (default: structure.json)",
    )
    args = parser.parse_args()

    count = write_chunks(args.source.resolve(), args.output.resolve())
    print(f"Wrote {count} chunks to {args.output.resolve()}")


if __name__ == "__main__":
    main()
