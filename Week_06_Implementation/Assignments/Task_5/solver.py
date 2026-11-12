"""Implement the missing playground methods using the local RAG pipeline."""

from __future__ import annotations

import argparse
import ast
import importlib.util
import json
import os
import subprocess
import sys
import textwrap
from pathlib import Path
from typing import Any, Callable


ALLOWED_MODELS = (
    "gpt-6-luna",
    "gpt-5.6-luna",
    "gpt-5.4-nano",
    "gpt-5-nano",
    "gpt-5-mini",
    "gpt-4.1-nano",
    "gpt-4o-mini",
)
DEFAULT_MODEL = "gpt-5.6-luna"
Completion = Callable[[str, str, str], str]


def _load_module(name: str, path: Path):
    spec = importlib.util.spec_from_file_location(name, path)
    if spec is None or spec.loader is None:
        raise ImportError(f"Could not load module from {path}")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def _target_method(
    source: str, class_name: str, method_name: str
) -> tuple[ast.ClassDef, ast.FunctionDef | ast.AsyncFunctionDef]:
    tree = ast.parse(source)
    for node in tree.body:
        if isinstance(node, ast.ClassDef) and node.name == class_name:
            for member in node.body:
                if (
                    isinstance(member, (ast.FunctionDef, ast.AsyncFunctionDef))
                    and member.name == method_name
                ):
                    return node, member
            raise ValueError(f"Method {class_name}.{method_name} not found")
    raise ValueError(f"Class {class_name} not found")


def _method_source(
    source: str, class_name: str, method_name: str
) -> tuple[str, ast.FunctionDef | ast.AsyncFunctionDef]:
    _, method = _target_method(source, class_name, method_name)
    lines = source.splitlines(keepends=True)
    start = min(
        [method.lineno, *(decorator.lineno for decorator in method.decorator_list)]
    )
    end = method.end_lineno or method.lineno
    return "".join(lines[start - 1 : end]), method


def _extract_body(response: str) -> str:
    response = response.strip("\r\n")
    if response.lstrip().startswith("```"):
        response = response.strip()
        lines = response.splitlines()
        if len(lines) < 3 or not lines[-1].strip().startswith("```"):
            raise ValueError("LLM returned an unterminated code fence")
        response = "\n".join(lines[1:-1])
    body = textwrap.dedent(response).strip()
    if not body:
        raise ValueError("LLM returned an empty method body")
    if body.lstrip().startswith(("def ", "async def ", "class ")):
        raise ValueError("LLM must return the method body only, not a definition")

    indented = textwrap.indent(body, "    ")
    try:
        parsed = ast.parse(f"def _generated_method():\n{indented}\n")
    except SyntaxError as error:
        raise ValueError(f"LLM returned invalid Python: {error}") from error
    statements = parsed.body[0].body
    if len(statements) == 1 and isinstance(statements[0], ast.Pass):
        raise ValueError("LLM returned only 'pass'")
    return body


def _body_replacement(
    source: str,
    class_name: str,
    method_name: str,
    body: str,
) -> tuple[int, int, list[str]]:
    _, method = _target_method(source, class_name, method_name)
    lines = source.splitlines(keepends=True)
    statements = list(method.body)
    if statements and isinstance(statements[0], ast.Expr) and isinstance(
        statements[0].value, ast.Constant
    ) and isinstance(statements[0].value.value, str):
        statements = statements[1:]
        first_line = (method.body[0].end_lineno or method.body[0].lineno) + 1
    else:
        first_line = statements[0].lineno if statements else (method.end_lineno or method.lineno) + 1
    end_line = (method.end_lineno or method.lineno) if statements else first_line - 1

    indentation = " " * (method.col_offset + 4)
    replacement = [indentation + line + "\n" if line else "\n" for line in body.splitlines()]
    if not replacement:
        raise ValueError("Method body must not be empty")
    if lines and not lines[-1].endswith(("\n", "\r")) and end_line == len(lines):
        replacement[-1] = replacement[-1].rstrip("\n")
    return first_line - 1, end_line, replacement


def _apply_replacements(
    original: str,
    changes: list[tuple[str, str, str]],
) -> str:
    replacements = []
    for class_name, method_name, body in changes:
        start, end, lines = _body_replacement(
            original, class_name, method_name, body
        )
        replacements.append((start, end, lines))

    updated = original.splitlines(keepends=True)
    for start, end, replacement in sorted(replacements, key=lambda item: item[0], reverse=True):
        updated[start:end] = replacement
    result = "".join(updated)
    ast.parse(result)
    return result


def solve_task(
    task_text: str,
    target_file: Path,
    class_name: str,
    method_name: str,
    source_text: str,
    chunks: dict[str, Any],
    embeddings: dict[str, Any],
    model: str,
    complete: Completion,
    top_k: int = 5,
) -> str:
    """Retrieve context and return validated Python statements for one method."""
    if model not in ALLOWED_MODELS:
        raise ValueError(f"Model must be one of: {', '.join(ALLOWED_MODELS)}")

    _, method = _target_method(source_text, class_name, method_name)
    method_text, _ = _method_source(source_text, class_name, method_name)
    embedder_path = Path(__file__).resolve().parents[1] / "Task_3" / "embeder.py"
    chooser_path = Path(__file__).resolve().parents[1] / "Task_4" / "chooser.py"
    embedder = _load_module("task3_embeder", embedder_path)
    chooser = _load_module("task4_chooser", chooser_path)

    query = (
        f"Implement {class_name}.{method_name} in {target_file}.\n"
        f"Requirements: {task_text}\n"
        f"Existing method signature and decorators:\n{method_text}"
    )
    query_vector = embedder.embed_text(
        query,
        embeddings["idf"],
        embeddings["document_count"],
        embeddings["dimensions"],
    )
    matches = chooser.choose_chunks(query_vector, embeddings, top_k, query_text=query)
    chunks_by_id = {chunk["id"]: chunk for chunk in chunks["chunks"]}
    retrieved = []
    for match in matches:
        chunk = chunks_by_id.get(match["id"])
        if chunk is not None:
            retrieved.append(
                {
                    "id": match["id"],
                    "path": chunk["path"],
                    "name": chunk["name"],
                    "text": chunk["text"],
                }
            )

    system_prompt = (
        "You are implementing one missing Python method in an existing project. "
        "Use the supplied task and retrieved repository chunks as context. "
        "Return only the method body statements as valid Python; do not include "
        "a function/class definition, Markdown fences, or explanations. Preserve "
        "the method's existing signature and decorators. Do not modify unrelated code."
    )
    user_prompt = json.dumps(
        {
            "task": task_text,
            "target": f"{target_file}::{class_name}.{method_name}",
            "method_source": method_text,
            "retrieved_chunks": retrieved,
        },
        ensure_ascii=False,
        indent=2,
    )
    generated = complete(model, system_prompt, user_prompt)
    return _extract_body(generated)


def _completion_from_openai(model: str, system_prompt: str, user_prompt: str) -> str:
    from openai import OpenAI

    response = OpenAI().chat.completions.create(
        model=model,
        messages=[
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_prompt},
        ],
        max_completion_tokens=1200,
    )
    content = response.choices[0].message.content
    if not content:
        raise RuntimeError(f"The model {model} returned an empty response")
    return content


def run_tasks(
    tasks: list[dict[str, str]],
    source_root: Path,
    chunks_path: Path,
    embeddings_path: Path,
    model: str,
    complete: Completion,
    dry_run: bool = False,
) -> dict[str, Any]:
    if model not in ALLOWED_MODELS:
        raise ValueError(f"Model must be one of: {', '.join(ALLOWED_MODELS)}")
    root = source_root.resolve()
    chunks = json.loads(chunks_path.read_text(encoding="utf-8"))
    embeddings = json.loads(embeddings_path.read_text(encoding="utf-8"))
    pending: dict[Path, list[tuple[str, str, str]]] = {}

    for index, task in enumerate(tasks, start=1):
        required = {"file", "class", "method", "docstring"}
        missing = required - task.keys()
        if missing:
            raise ValueError(f"Task {index} is missing fields: {sorted(missing)}")
        target = (root / task["file"]).resolve()
        if not target.is_relative_to(root):
            raise ValueError(f"Task target escapes source root: {task['file']}")
        source_text = target.read_text(encoding="utf-8")
        task_text = (
            f"Implement {task['class']}.{task['method']}. "
            f"Required behavior: {task['docstring'].strip()}"
        )
        body = solve_task(
            task_text,
            Path(task["file"]),
            task["class"],
            task["method"],
            source_text,
            chunks,
            embeddings,
            model,
            complete,
        )
        pending.setdefault(target, []).append(
            (task["class"], task["method"], body)
        )
        print(
            f"Generated {task['file']}::{task['class']}.{task['method']} "
            f"({index}/{len(tasks)})",
            flush=True,
        )

    updated_files = {}
    for target, changes in pending.items():
        original = target.read_text(encoding="utf-8")
        updated_files[target] = _apply_replacements(original, changes)

    if not dry_run:
        for target, updated in updated_files.items():
            target.write_text(updated, encoding="utf-8")

    return {
        "tasks_completed": len(tasks),
        "files_changed": [str(path) for path in updated_files],
        "dry_run": dry_run,
    }


def _run_project_tests(project_root: Path) -> int:
    command = [
        sys.executable,
        "-m",
        "unittest",
        "discover",
        "-s",
        "tests",
        "-p",
        "test_*.py",
    ]
    result = subprocess.run(command, cwd=project_root, check=False)
    return result.returncode


def main() -> None:
    task_directory = Path(__file__).resolve().parent
    assignments = task_directory.parent
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--tasks",
        type=Path,
        default=assignments / "missing_code.json",
        help="JSON file describing methods to implement",
    )
    parser.add_argument(
        "--source-root",
        type=Path,
        default=assignments / "Task_1" / "cloned_repo",
        help="root of the cloned repository",
    )
    parser.add_argument(
        "--chunks",
        type=Path,
        default=assignments / "Task_2" / "structure.json",
    )
    parser.add_argument(
        "--embeddings",
        type=Path,
        default=assignments / "Task_3" / "embeddings.json",
    )
    parser.add_argument("--model", choices=ALLOWED_MODELS, default=DEFAULT_MODEL)
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="generate and validate all implementations without writing files",
    )
    parser.add_argument(
        "--run-tests",
        action="store_true",
        help="run the cloned repository's unittest suite after writing changes",
    )
    args = parser.parse_args()

    env_file = task_directory / ".env"
    try:
        from dotenv import load_dotenv
    except ImportError as error:
        raise SystemExit(
            "Missing dependencies. Install them with: "
            f"{sys.executable} -m pip install -r {task_directory / 'requirements.txt'}"
        ) from error
    load_dotenv(env_file)
    api_key = os.getenv("OPENAI_API_KEY")
    if not api_key or api_key == "your-openai-api-key-here":
        raise SystemExit(
            f"Set OPENAI_API_KEY in {env_file} before calling the model."
        )

    tasks = json.loads(args.tasks.read_text(encoding="utf-8"))
    result = run_tasks(
        tasks,
        args.source_root,
        args.chunks,
        args.embeddings,
        args.model,
        _completion_from_openai,
        dry_run=args.dry_run,
    )
    print(json.dumps(result, indent=2))
    if args.run_tests and not args.dry_run:
        test_code = _run_project_tests(args.source_root / "playground")
        print(f"Project unittest exit code: {test_code}")
        if test_code:
            raise SystemExit(test_code)


if __name__ == "__main__":
    main()
