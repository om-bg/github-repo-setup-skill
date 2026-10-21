"""Opt-in disposable tests calling the shipped implementation."""

import argparse
import base64
import json
import os
from pathlib import Path
import re
import shutil
import subprocess
import tempfile
import unittest
from urllib.parse import quote
import uuid

LIVE, OWNER, HOST = False, None, "github.com"
ROOT = Path(__file__).resolve().parents[1] / "skills/github-repo-setup"


from runtime import GitHub, GitHubFailure, Workflow, failure_category


class DisposableGitHubTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        if not LIVE:
            raise unittest.SkipTest("Live GitHub writes are opt-in; see tests/README.md")
        cls.gh = GitHub(HOST)
        identity, headers = cls.gh.request("user", headers=True)
        if not OWNER or identity["login"].casefold() != OWNER.casefold():
            raise RuntimeError("Live owner must match the active personal account")
        scope_line = re.search(r"^x-oauth-scopes:[ \t]*(.*)$", headers, re.I | re.M)
        scopes = {value.strip() for value in scope_line[1].split(",")} if scope_line else set()
        if not {"repo", "project", "delete_repo"} <= scopes:
            raise unittest.SkipTest("Live setup needs reported repo/project/delete_repo scopes for guarded cleanup; no resources created")
        cls.name = "repo-workflow-test-" + uuid.uuid4().hex[:16]
        cls.repo = f"{identity['login']}/{cls.name}"
        cls.repo_id = cls.project_id = None
        cls.state = {"host": HOST, "owner": identity["login"], "run_name": cls.name, "repository": cls.repo, "phase": "starting"}
        cls.journal = Path(tempfile.mkdtemp(prefix="repo-workflow-tests-")) / "resources.json"
        cls.save_state()
        print(f"\nDisposable fixture journal: {cls.journal}", flush=True)
        cls.addClassCleanup(cls.cleanup)
        cls.state["phase"] = "repository_create_outcome_unknown"
        cls.save_state()
        repository = cls.gh.request("user/repos", "POST", {"name": cls.name, "private": True, "auto_init": False, "has_issues": True, "description": cls.name})
        cls.repo_id = repository["node_id"]
        cls.state.update(repository_id=cls.repo_id, repository_url=repository["html_url"], phase="repository_created")
        cls.save_state()
        owner_id = cls.gh.graphql("query{viewer{id}}")["viewer"]["id"]
        cls.state["phase"] = "project_create_outcome_unknown"
        cls.save_state()
        project = cls.gh.graphql("mutation($input:CreateProjectV2Input!){createProjectV2(input:$input){projectV2{id url number}}}", {"input": {"ownerId": owner_id, "title": cls.name}}, write=True)["createProjectV2"]["projectV2"]
        cls.project_id = project["id"]
        cls.state.update(project_id=cls.project_id, project_url=project["url"], phase="project_created")
        cls.save_state()
        cls.gh.graphql("mutation($input:UpdateProjectV2Input!){updateProjectV2(input:$input){projectV2{id public}}}", {"input": {"projectId": cls.project_id, "public": False}}, write=True)
        cls.gh.graphql("mutation($input:LinkProjectV2ToRepositoryInput!){linkProjectV2ToRepository(input:$input){repository{id}}}", {"input": {"projectId": cls.project_id, "repositoryId": cls.repo_id}}, write=True)
        cls.workflow = Workflow(cls.gh, cls.repo, project["number"])
        cls.state["phase"] = "ready"
        cls.save_state()

    @classmethod
    def save_state(cls):
        cls.journal.write_text(json.dumps(cls.state, indent=2) + "\n", encoding="utf-8")

    @classmethod
    def cleanup(cls):
        failures = []
        if cls.project_id:
            try:
                project = cls.gh.graphql("query($id:ID!){node(id:$id){... on ProjectV2{id title owner{... on User{login}}}}}", {"id": cls.project_id})["node"]
                if not project or project["id"] != cls.project_id or project["title"] != cls.name or project["owner"]["login"].casefold() != OWNER.casefold():
                    raise RuntimeError("Project cleanup identity check failed")
                cls.gh.graphql("mutation($input:DeleteProjectV2Input!){deleteProjectV2(input:$input){clientMutationId}}", {"input": {"projectId": cls.project_id}}, write=True)
                cls.state["project_deleted"] = True
            except Exception as error:
                failures.append(str(error) if isinstance(error, GitHubFailure) else "Project cleanup failed identity/API checks")
        if cls.repo_id:
            try:
                repository = cls.gh.request(f"repos/{cls.repo}")
                if repository["node_id"] != cls.repo_id or repository["full_name"].casefold() != cls.repo.casefold() or repository["description"] != cls.name:
                    raise RuntimeError("Repository cleanup identity check failed")
                cls.gh.request(f"repos/{cls.repo}", "DELETE")
                cls.state["repository_deleted"] = True
            except Exception as error:
                failures.append(str(error) if isinstance(error, GitHubFailure) else "Repository cleanup failed identity/API checks")
        cls.state["cleanup_errors"] = failures
        cls.save_state()
        if failures:
            raise RuntimeError("Cleanup incomplete; inspect journal. " + "; ".join(failures))

    def prepare_fields_and_board(self):
        for name, options in (("Status", ["Backlog", "Ready", "In progress", "Review / Test", "Complete"]), ("Priority", ["P0", "P1", "P2"])):
            plan = self.workflow.plan_field(name, options)
            self.assertTrue(self.workflow.apply_field(plan, approved=True)["verified"])
        plan = self.workflow.plan_board("Test board", ["Title", "Status", "Priority"])
        result = self.workflow.apply_board(plan, approved=True)
        self.assertTrue(result["verified"], result)

    def test_00_empty_repository(self):
        repository = self.gh.request(f"repos/{self.repo}")
        self.assertTrue(repository["private"])
        self.assertEqual(repository["size"], 0)
        actual = self.workflow.audit()
        self.assertTrue(actual["linked"])
        self.assertEqual(sum(field.get("name") == "Status" for field in actual["fields"]), 1)

    def test_10_existing_configuration(self):
        kept = self.workflow.label("keep-me", "123456", "Unrelated", approved=True)
        existing = self.gh.request(f"repos/{self.repo}/labels/bug")
        actual = self.workflow.label("bug", "654321", "Updated", approved=True)
        self.assertEqual(existing["id"], actual["id"])
        self.assertEqual(kept["id"], self.workflow.label("keep-me", "123456", "Unrelated", approved=True)["id"])

    def test_20_missing_write_permission(self):
        if not os.environ.get("REPO_SETUP_READ_ONLY_TOKEN"):
            self.skipTest("No restricted fixture-readable credential supplied")
        restricted = Workflow(GitHub(HOST, "REPO_SETUP_READ_ONLY_TOKEN"), self.repo)
        with self.assertRaises(GitHubFailure) as failure:
            restricted.label("denied-write", "123456", "Must not be created", approved=True)
        self.assertEqual(failure.exception.category, "authorization")

    def test_30_partial_setup_and_lost_response(self):
        original = self.gh.request
        created_id = None
        def lost_response(endpoint, method="GET", *args, **kwargs):
            nonlocal created_id
            result = original(endpoint, method, *args, **kwargs)
            if endpoint.endswith("/labels") and method == "POST":
                created_id = result["id"]
                raise GitHubFailure("network", uncertain=True)
            return result
        from unittest.mock import patch
        with patch.object(self.gh, "request", side_effect=lost_response):
            with self.assertRaises(GitHubFailure):
                self.workflow.label("resume-after-write", "123456", "Resume", approved=True)
        self.assertEqual(created_id, self.workflow.label("resume-after-write", "123456", "Resume", approved=True)["id"])
        self.prepare_fields_and_board()

    def test_40_repeated_execution(self):
        self.prepare_fields_and_board()
        first = self.workflow.audit()
        self.prepare_fields_and_board()
        self.assertEqual(first, self.workflow.audit())

    def test_50_creation_and_read_back(self):
        self.prepare_fields_and_board()
        self.workflow.label("type:bug", "D73A4A", "Bug", approved=True)
        issue = self.gh.request(f"repos/{self.repo}/issues", "POST", {"title": "Disposable verification issue", "labels": ["type:bug"]})
        values = {"Status": "Backlog", "Priority": "P1"}
        first = self.workflow.associate(issue["number"], values, approved=True)
        self.assertTrue(first["verified"])
        self.assertEqual(first, self.workflow.associate(issue["number"], values, approved=True))
        for name in ("task.yml", "bug.yml", "config.yml"):
            value = (ROOT / "assets/issue-templates" / name).read_bytes()
            path = f".github/ISSUE_TEMPLATE/{name}"
            first_sha = self.workflow.content(path, value, approved=True)
            self.assertEqual(first_sha, self.workflow.content(path, value, approved=True))

    def test_60_status_priority_preserve_populated_assignments(self):
        self.prepare_fields_and_board()
        issue = self.gh.request(f"repos/{self.repo}/issues", "POST", {"title": "Populated fields"})
        self.workflow.associate(issue["number"], {"Status": "Backlog", "Priority": "P0"}, approved=True)
        assignments = self.workflow.assignments()
        for name, additions in (("Status", ["In Review"]), ("Priority", ["P3"])):
            plan = self.workflow.plan_field(name, additions)
            self.assertTrue(self.workflow.apply_field(plan, approved=True)["verified"])
            self.assertTrue(self.workflow.verify_field(plan))
            self.assertEqual(assignments, self.workflow.assignments())

    def test_70_template_branch_and_pr_routes(self):
        repository = self.gh.request(f"repos/{self.repo}")
        base = repository["default_branch"]
        original = self.gh.request(f"repos/{self.repo}/git/ref/heads/{quote(base, safe='')}")["object"]["sha"]
        files = {".github/pull_request_template.md": b"## Outcome\n\nDescribe the result.\n"}
        branch_result = self.workflow.publish_templates(files, "branch", branch="setup/templates", base=base, approved=True)
        self.assertTrue(branch_result["verified"])
        self.assertFalse(branch_result["active_on_default_branch"])
        options = {"branch": "setup/templates", "base": base, "title": "Workflow templates", "body": "Disposable publication verification", "approved": True}
        first = self.workflow.publish_templates(files, "pr", **options)
        self.assertEqual(first, self.workflow.publish_templates(files, "pr", **options))
        self.assertEqual(original, self.gh.request(f"repos/{self.repo}/git/ref/heads/{quote(base, safe='')}")["object"]["sha"])



if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--live", action="store_true", help="Allow this run's disposable creation, writes, and guarded cleanup")
    parser.add_argument("--owner", help="Active personal account; required for live tests")
    parser.add_argument("--host", default="github.com")
    arguments, remaining = parser.parse_known_args()
    if arguments.live and not arguments.owner:
        parser.error("--owner is required with --live")
    LIVE, OWNER, HOST = arguments.live, arguments.owner, arguments.host
    unittest.main(argv=[__file__, *remaining], verbosity=2)
