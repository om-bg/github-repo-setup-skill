"""Exercise the installed command entry point, not a second publication recipe."""
from contextlib import redirect_stderr, redirect_stdout
import io
import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

from fake_github import FakeGitHub
import github_workflow


class PublishingCommandTests(unittest.TestCase):
    def setUp(self):
        self.api = FakeGitHub()
        self.directory = tempfile.TemporaryDirectory(prefix="workflow-command-")
        self.addCleanup(self.directory.cleanup)
        root = Path(self.directory.name)
        self.template, self.body = root / "draft.md", root / "description.md"
        self.template.write_bytes(b"## Outcome\n")
        self.body.write_text("Publish the reviewed template.", encoding="utf-8")
        self.arguments = ["publish-templates", "--repo", "example/remote", "--route", "pr",
                          "--branch", "setup/templates", "--template", ".github/pull_request_template.md", str(self.template),
                          "--title", "Workflow templates", "--body-file", str(self.body), "--approved"]

    def invoke(self, arguments):
        output, error = io.StringIO(), io.StringIO()
        with patch.object(github_workflow, "GitHub", return_value=self.api), redirect_stdout(output), redirect_stderr(error):
            result = github_workflow.main(arguments)
        return result, json.loads(output.getvalue() or error.getvalue())

    def test_cli_publishes_pr_without_project_and_repeat_reuses_everything(self):
        code, first = self.invoke(self.arguments)
        self.assertEqual(code, 0)
        self.assertTrue(first["verified"])
        self.assertFalse(first["active_on_default_branch"])
        self.assertIn("pull_request", first)
        writes = list(self.api.writes)
        self.assertEqual((code, first), self.invoke(self.arguments))
        self.assertEqual(writes, self.api.writes)
        self.assertEqual(self.api.branches["main"], "initial")

    def test_missing_approval_or_route_fails_before_discovery(self):
        for arguments in (self.arguments[:-1], ["publish-templates", "--repo", "example/remote", "--approved"]):
            with self.subTest(arguments=arguments):
                self.assertEqual(self.invoke(arguments)[0], 1)
                self.assertFalse(self.api.calls)
                self.assertFalse(self.api.writes)

    def test_protected_input_is_rejected_before_reading_other_inputs(self):
        arguments = self.arguments + ["--template", ".github/ISSUE_TEMPLATE/task.yml", "Secret.MD"]
        with patch.object(Path, "read_bytes") as read:
            self.assertEqual(self.invoke(arguments), (1, {"error": "protected_input", "status": None, "outcome_unknown": False}))
        read.assert_not_called()
        self.assertFalse(self.api.calls)

    def test_duplicate_remote_paths_are_rejected_before_reading(self):
        with patch.object(Path, "read_bytes") as read:
            code, result = self.invoke(self.arguments + ["--template", ".github/pull_request_template.md", "another.md"])
        self.assertEqual(code, 1)
        self.assertEqual(result["error"], "invalid_input")
        read.assert_not_called()
        self.assertFalse(self.api.calls)

    def test_project_operation_still_requires_project(self):
        self.assertEqual(self.invoke(["audit", "--repo", "example/remote"])[1]["error"], "missing_project")
        self.assertFalse(self.api.calls)

    def test_status_cleanup_is_exposed_as_a_reviewable_plan(self):
        code, plan = self.invoke(["plan-field", "--repo", "example/remote", "--project", "2", "--name", "Status",
                                  "--options", "Backlog", "Ready", "In progress", "Review / Test", "Complete", "--remove-unused-default-statuses"])
        self.assertEqual(code, 0)
        self.assertEqual([option["name"] for option in plan["options"]], ["Backlog", "Ready", "In progress", "Review / Test", "Complete"])
        self.assertEqual({option["name"] for option in plan["removed"]}, {"Todo", "Done"})
        self.assertFalse(self.api.writes)


if __name__ == "__main__":
    unittest.main()
