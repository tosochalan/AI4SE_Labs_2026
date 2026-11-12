import json
import tempfile
import unittest
from pathlib import Path

from solver import _apply_replacements, _extract_body, run_tasks, solve_task


class ExtractBodyTests(unittest.TestCase):
    def test_extracts_indented_or_fenced_body(self):
        self.assertEqual(_extract_body("    if value:\n        return True"), "if value:\n    return True")
        self.assertEqual(_extract_body("```python\nreturn 3\n```"), "return 3")

    def test_rejects_invalid_or_incomplete_responses(self):
        for response in ("", "pass", "def method(self):\n    return 1", "return ("):
            with self.subTest(response=response):
                with self.assertRaises(ValueError):
                    _extract_body(response)


class MethodReplacementTests(unittest.TestCase):
    def test_replaces_only_the_requested_method_body(self):
        original = (
            "class Example:\n"
            "    def first(self):\n"
            "        pass\n\n"
            "    def second(self):\n"
            "        pass\n"
        )
        updated = _apply_replacements(
            original,
            [
                ("Example", "first", "return 1"),
                ("Example", "second", "return 2"),
            ],
        )
        self.assertIn("    def first(self):\n        return 1", updated)
        self.assertIn("    def second(self):\n        return 2", updated)
        compile(updated, "<updated>", "exec")

    def test_preserves_decorator_and_existing_docstring(self):
        original = (
            "class Example:\n"
            "    @property\n"
            "    def ready(self):\n"
            '        """Readiness state."""\n'
            "        pass\n"
        )
        updated = _apply_replacements(original, [("Example", "ready", "return True")])
        self.assertIn("@property\n    def ready", updated)
        self.assertIn('"""Readiness state."""\n        return True', updated)


class SolveTaskTests(unittest.TestCase):
    def test_retrieves_five_chunks_and_validates_completion(self):
        with tempfile.TemporaryDirectory() as temporary_directory:
            root = Path(temporary_directory)
            source = "class Example:\n    def ready(self):\n        pass\n"
            chunk_records = []
            embedding_records = []
            for index in range(6):
                chunk_id = f"chunk-{index}"
                chunk_records.append(
                    {
                        "id": chunk_id,
                        "path": f"example_{index}.py",
                        "name": f"example_{index}",
                        "text": f"Useful context {index}",
                    }
                )
                embedding_records.append(
                    {"id": chunk_id, "embedding": [1.0, float(index)]}
                )
            chunks = {"chunks": chunk_records}
            embeddings = {
                "idf": {},
                "document_count": len(chunk_records),
                "dimensions": 2,
                "embeddings": embedding_records,
            }
            calls = []

            def completion(model, system_prompt, user_prompt):
                calls.append((model, system_prompt, json.loads(user_prompt)))
                return "return True"

            body = solve_task(
                "Return whether this object is ready.",
                Path("example.py"),
                "Example",
                "ready",
                source,
                chunks,
                embeddings,
                "gpt-5.6-luna",
                completion,
            )
            self.assertEqual(body, "return True")
            self.assertEqual(calls[0][0], "gpt-5.6-luna")
            self.assertEqual(len(calls[0][2]["retrieved_chunks"]), 5)

    def test_rejects_unapproved_model_without_calling_completion(self):
        with self.assertRaisesRegex(ValueError, "Model must be one of"):
            solve_task(
                "Task",
                Path("example.py"),
                "Example",
                "ready",
                "class Example:\n    def ready(self):\n        pass\n",
                {"chunks": []},
                {},
                "unapproved-model",
                lambda *_: self.fail("completion must not be called"),
            )

    def test_run_tasks_dry_run_does_not_modify_source(self):
        with tempfile.TemporaryDirectory() as temporary_directory:
            root = Path(temporary_directory)
            target = root / "example.py"
            original = "class Example:\n    def ready(self):\n        pass\n"
            target.write_text(original, encoding="utf-8")
            chunks_path = root / "chunks.json"
            embeddings_path = root / "embeddings.json"
            chunks = {"chunks": [{"id": "c1", "path": "example.py", "name": "ready", "text": original}]}
            embeddings = {
                "idf": {},
                "document_count": 1,
                "dimensions": 2,
                "embeddings": [{"id": "c1", "embedding": [1.0, 0.0]}],
            }
            chunks_path.write_text(json.dumps(chunks), encoding="utf-8")
            embeddings_path.write_text(json.dumps(embeddings), encoding="utf-8")
            result = run_tasks(
                [{"file": "example.py", "class": "Example", "method": "ready", "docstring": "Return true."}],
                root,
                chunks_path,
                embeddings_path,
                "gpt-5.6-luna",
                lambda *_: "return True",
                dry_run=True,
            )
            self.assertTrue(result["dry_run"])
            self.assertEqual(target.read_text(encoding="utf-8"), original)


if __name__ == "__main__":
    unittest.main()
