import contextlib
import importlib.util
import io
import json
import tempfile
import unittest
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import patch


MODULE_PATH = Path(__file__).with_name("requirements_network.py")
SPEC = importlib.util.spec_from_file_location("requirements_network", MODULE_PATH)
assert SPEC is not None and SPEC.loader is not None
network = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(network)


class RequirementsNetworkTests(unittest.TestCase):
    source = "corpus/email_report_features.eml"

    def requirement(self, **updates):
        item = {
            "id": "REQ-001",
            "name": "Report Queue",
            "description": "The system shall expose report queue status to authorized staff users.",
            "priority": "High",
            "priority_rationale": "Core workflow.",
            "sources": [self.source],
            "notes": "",
        }
        item.update(updates)
        return item

    def quality_gate(self, requirements, blacklist=None):
        return network.deterministic_quality_gate({
            "requirements": requirements,
            "blacklist": blacklist or [],
            "documents": [{"name": self.source}],
        })

    def test_revision_accepts_new_complete_requirement_and_quality_gate_assigns_id(self):
        original = self.requirement()
        new_requirement = {
            "id": "REQ-065",
            "name": "Multi-Report Selection and Recipient Address Book",
            "description": (
                "Authorized users shall be able to run or schedule several reports "
                "together and select email recipients from a configured address book."
            ),
            "priority": "High",
            "priority_rationale": "The reviewer identified this omission.",
            "sources": [self.source],
            "notes": "Added from a source-backed reviewer finding.",
        }

        result = network._merge_revision_results([original, new_requirement], [original])[0]
        validated = self.quality_gate(result)

        self.assertEqual(len(validated["requirements"]), 2)
        self.assertEqual(validated["requirements"][1]["id"], "REQ-002")
        self.assertEqual(validated["requirements"][1]["name"], new_requirement["name"])

    def test_patch_revision_is_completed_and_omitted_existing_items_are_preserved(self):
        original = self.requirement()
        unchanged = self.requirement(
            id="REQ-002",
            name="Unchanged Requirement",
            description="The system shall preserve an unrelated requirement during revision.",
        )
        patch_item = {
            "id": original["id"],
            "name": original["name"],
            "revision": "Include a report queue position and current status.",
            "sources": [self.source],
        }
        complete_update = self.requirement(
            description=(
                "The system shall show report queue position, submission time, "
                "and current status to authorized staff users."
            )
        )
        responses = [
            {"requirements": [patch_item], "blacklist": []},
            {"requirements": [complete_update]},
        ]

        with patch.object(network, "_json_completion", side_effect=responses) as completion:
            with contextlib.redirect_stdout(io.StringIO()):
                result = network.revise_requirements({
                    "requirements": [original, unchanged],
                    "blacklist": [],
                    "review_issues": ["Show queue position and status."],
                })

        self.assertEqual(completion.call_count, 2)
        self.assertEqual(len(result["requirements"]), 2)
        self.assertIn("queue position", result["requirements"][0]["description"])
        self.assertEqual(result["requirements"][1]["name"], "Unchanged Requirement")
        self.quality_gate(result["requirements"])

    def test_incomplete_new_requirement_is_repaired_by_followup(self):
        original = self.requirement()
        incomplete = {"id": "REQ-002", "name": "New Requirement"}
        added = {
            "id": "REQ-002",
            "name": "New Requirement",
            "description": (
                "The system shall provide the newly identified report capability "
                "to authorized users."
            ),
            "priority": "Medium",
            "sources": [self.source],
        }
        with patch.object(
            network,
            "_json_completion",
            side_effect=[
                {"requirements": [original, incomplete], "blacklist": []},
                {"requirements": [added]},
            ],
        ):
            with contextlib.redirect_stdout(io.StringIO()):
                result = network.revise_requirements({
                    "requirements": [original],
                    "blacklist": [],
                    "review_issues": ["Add the omitted report capability."],
                })
        self.assertEqual(len(result["requirements"]), 2)
        self.assertEqual(result["requirements"][1]["name"], "New Requirement")
        self.quality_gate(result["requirements"])

    def test_still_incomplete_revision_has_actionable_error(self):
        original = self.requirement()
        incomplete = {"id": "REQ-001", "name": "Report Queue"}
        with patch.object(
            network,
            "_json_completion",
            side_effect=[
                {"requirements": [incomplete], "blacklist": []},
                {"requirements": [incomplete]},
            ],
        ):
            with contextlib.redirect_stdout(io.StringIO()):
                with self.assertRaisesRegex(ValueError, "incomplete requirement objects"):
                    network.revise_requirements({
                        "requirements": [original],
                        "blacklist": [],
                        "review_issues": ["Complete the requirement."],
                    })

    def test_quality_gate_rejects_missing_fields_and_unknown_citations(self):
        with self.assertRaisesRegex(ValueError, "missing description"):
            self.quality_gate([{"name": "Incomplete", "priority": "High", "sources": [self.source]}])

        with self.assertRaisesRegex(ValueError, "Unknown source citation"):
            self.quality_gate([self.requirement(sources=["not-in-corpus.txt"])])

    def test_quality_gate_rejects_unknown_priorities(self):
        with self.assertRaisesRegex(ValueError, "Unknown priority"):
            self.quality_gate([self.requirement(priority="Urgent")])

    def test_quality_gate_rejects_malformed_blacklist_and_citations(self):
        with self.assertRaisesRegex(ValueError, "Malformed blacklist entry"):
            self.quality_gate([], blacklist=[{"description": "Discarded without a reason"}])

        with self.assertRaisesRegex(ValueError, "Unknown blacklist source citation"):
            self.quality_gate([], blacklist=[{
                "description": "Discarded text",
                "reason": "Not a requirement",
                "sources": ["not-in-corpus.txt"],
            }])

    def test_loader_rejects_empty_input_directory(self):
        with tempfile.TemporaryDirectory() as directory:
            with self.assertRaisesRegex(ValueError, "No .txt, .eml, or .md documents"):
                network.load_corpus({"input_dir": directory})

    def test_json_completion_rejects_empty_invalid_and_non_object_json(self):
        for content, error in (
            ("", "returned an empty response"),
            ("{invalid", "returned invalid JSON"),
            (json.dumps([]), "not an object"),
        ):
            message = SimpleNamespace(content=content)
            response = SimpleNamespace(choices=[SimpleNamespace(message=message)])
            client = SimpleNamespace(
                chat=SimpleNamespace(
                    completions=SimpleNamespace(create=lambda **kwargs: response)
                )
            )
            with self.subTest(content=content), patch.object(network, "OpenAI", return_value=client):
                with contextlib.redirect_stdout(io.StringIO()):
                    with self.assertRaisesRegex(ValueError, error):
                        network._json_completion("test-model", "system", "user")


if __name__ == "__main__":
    unittest.main()
