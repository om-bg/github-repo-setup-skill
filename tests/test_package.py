"""Offline package checks and failure-path tests; never contact GitHub."""

import json
from pathlib import Path
import re
import subprocess
from types import SimpleNamespace
import unittest
from unittest.mock import Mock, patch

import yaml
import test_github_integration as integration

ROOT = Path(__file__).resolve().parents[1]
DOCUMENTS = [
    "SKILL.md", "README.md", "REVIEW.md", "references/authentication.md",
    "references/workflow-design.md", "references/github-operations.md",
    "references/security-and-recovery.md", "references/configuration.md",
    "references/troubleshooting.md", "references/validation-scenarios.md", "tests/README.md",
]


class PackageTests(unittest.TestCase):
    def test_agent_skills_metadata(self):
        text = (ROOT / "SKILL.md").read_text(encoding="utf-8")
        match = re.match(r"\A---\n(.*?)\n---\n", text, re.S)
        self.assertIsNotNone(match)
        metadata = yaml.safe_load(match[1])
        self.assertEqual(metadata["name"], ROOT.name)
        self.assertRegex(metadata["name"], r"^[a-z0-9]+(?:-[a-z0-9]+)*$")
        self.assertLessEqual(len(metadata["name"]), 64)
        self.assertTrue(0 < len(metadata["description"]) <= 1024)
        self.assertTrue(all(isinstance(key, str) and isinstance(value, str) for key, value in metadata.get("metadata", {}).items()))

    def test_internal_links_stay_in_package(self):
        for name in DOCUMENTS:
            path = ROOT / name
            for target in re.findall(r"\[[^\]]*\]\(([^)]+)\)", path.read_text(encoding="utf-8")):
                if target.startswith(("https://", "http://", "#")):
                    continue
                destination = (path.parent / target.split("#", 1)[0]).resolve()
                self.assertTrue(destination.is_relative_to(ROOT), (name, target))
                self.assertNotEqual(destination.name.lower(), "secret.md")
                self.assertTrue(destination.exists(), (name, target))

    def test_issue_forms_and_label_references(self):
        labels = json.loads((ROOT / "assets/labels.json").read_text(encoding="utf-8"))
        names = {label["name"].casefold() for label in labels}
        self.assertEqual(len(names), len(labels))
        for label in labels:
            self.assertRegex(label["color"], r"^[0-9A-Fa-f]{6}$")
            self.assertLessEqual(len(label["description"]), 100)
        for name in ("task.yml", "bug.yml", "experiment.yml"):
            data = yaml.safe_load((ROOT / "assets/issue-templates" / name).read_text(encoding="utf-8"))
            self.assertTrue(data["name"] and data["description"] and data["body"])
            ids = [item["id"] for item in data["body"] if "id" in item]
            self.assertEqual(len(ids), len(set(ids)))
            self.assertTrue({label.casefold() for label in data.get("labels", [])} <= names)
            for item in data["body"]:
                self.assertIn(item["type"], {"textarea", "input", "checkboxes", "dropdown", "markdown"})
                self.assertTrue(item["type"] == "markdown" or item["attributes"].get("label"))
        chooser = yaml.safe_load((ROOT / "assets/issue-templates/config.yml").read_text(encoding="utf-8"))
        self.assertIsInstance(chooser["blank_issues_enabled"], bool)

    def test_example_config_is_consistent(self):
        data = yaml.safe_load((ROOT / "assets/repo-workflow.example.yml").read_text(encoding="utf-8"))
        self.assertEqual(data["version"], 1)
        self.assertEqual(set(data), {"version", "labels", "templates", "project"})
        names = {label["name"] for label in data["labels"]}
        for form in data["templates"]["issues"]:
            asset = yaml.safe_load((ROOT / "assets/issue-templates" / (form + ".yml")).read_text(encoding="utf-8"))
            self.assertTrue(set(asset.get("labels", [])) <= names)
        statuses = {option["name"] for option in data["project"]["statuses"]}
        self.assertEqual(len(statuses), len(data["project"]["statuses"]))
        for view in data["project"]["views"]:
            self.assertIn(view["layout"], {"board", "table"})
            self.assertTrue("status" not in view or view["status"] in statuses)


class TransportTests(unittest.TestCase):
    @patch.object(integration.shutil, "which", return_value=None)
    @patch.object(integration.subprocess, "run")
    def test_missing_cli_is_actionable(self, run, which):
        with self.assertRaises(integration.GitHubFailure) as error:
            integration.GitHub().request("user")
        self.assertEqual(error.exception.category, "missing_tool")
        run.assert_not_called()

    def test_error_categories(self):
        for status, body, stderr, category in (
            (401, {}, "", "authentication"),
            (403, {}, "", "authorization"),
            (403, {"message": "API rate limit exceeded"}, "", "throttling"),
            (404, {}, "", "missing_or_hidden"),
            (409, {}, "", "conflict"),
            (422, {}, "", "api"),
            (None, {"errors": [{"type": "FORBIDDEN"}]}, "", "authorization"),
            (None, {}, "proxyconnect: connection refused", "network"),
        ):
            with self.subTest(category=category, status=status):
                self.assertEqual(integration.failure_category(status, body, stderr), category)

    @patch.object(integration.shutil, "which", return_value="gh")
    @patch.object(integration.subprocess, "run")
    def test_untrusted_text_is_json_data_not_shell_code(self, run, which):
        run.return_value = SimpleNamespace(returncode=0, stdout='{"id":1}', stderr="")
        payload = {"description": '$(unexpected-command); "untrusted" & echo ignored'}
        self.assertEqual(integration.GitHub().request("repos/example/fixture/labels", "POST", payload), {"id": 1})
        args, options = run.call_args
        self.assertIsInstance(args[0], list)
        self.assertFalse(options["shell"])
        self.assertEqual(json.loads(options["input"]), payload)
        self.assertNotIn(payload["description"], args[0])

    @patch.object(integration.shutil, "which", return_value="gh")
    @patch.object(integration.subprocess, "run")
    def test_http_200_graphql_partial_error_is_not_success(self, run, which):
        run.return_value = SimpleNamespace(returncode=0, stdout=json.dumps({"data": {"created": {"id": "fixture"}}, "errors": [{"type": "FORBIDDEN", "message": "private diagnostic value"}]}), stderr="")
        with self.assertRaises(integration.GitHubFailure) as error:
            integration.GitHub().graphql("mutation{fixture}", write=True)
        self.assertEqual(error.exception.category, "authorization")
        self.assertTrue(error.exception.uncertain)
        self.assertNotIn("private diagnostic value", str(error.exception))

    @patch.object(integration.shutil, "which", return_value="gh")
    @patch.object(integration.subprocess, "run", side_effect=subprocess.TimeoutExpired("gh", 45))
    def test_timed_out_write_has_unknown_outcome(self, run, which):
        with self.assertRaises(integration.GitHubFailure) as error:
            integration.GitHub().request("user/repos", "POST", {"name": "fixture"})
        self.assertEqual(error.exception.category, "network")
        self.assertTrue(error.exception.uncertain)

    def test_live_preflight_does_not_create_without_cleanup_access(self):
        client = Mock()
        client.request.return_value = ({"login": "example"}, "HTTP/2 200\nX-Oauth-Scopes: repo, project")
        with patch.multiple(integration, LIVE=True, OWNER="example"), patch.object(integration, "GitHub", return_value=client):
            with self.assertRaises(unittest.SkipTest):
                integration.DisposableGitHubTests.setUpClass()
        client.request.assert_called_once_with("user", headers=True)
        client.graphql.assert_not_called()

    def test_cleanup_refuses_resource_with_wrong_identity(self):
        client = Mock()
        client.graphql.return_value = {"node": {"id": "created-id", "title": "a-different-project", "owner": {"login": "example"}}}
        fixture = integration.DisposableGitHubTests
        with patch.multiple(integration, OWNER="example"), patch.multiple(fixture, gh=client, project_id="created-id", repo_id=None, name="this-run", state={}, create=True), patch.object(fixture, "save_state"):
            with self.assertRaises(RuntimeError):
                fixture.cleanup()
        self.assertEqual(client.graphql.call_count, 1)
        self.assertFalse(client.graphql.call_args.kwargs.get("write", False))
        client.request.assert_not_called()


if __name__ == "__main__":
    unittest.main(verbosity=2)
