"""Opt-in disposable tests of CLI/API recipes, not a setup executor."""

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
ROOT = Path(__file__).resolve().parents[1]


class GitHubFailure(RuntimeError):
    def __init__(self, category, status=None, uncertain=False):
        self.category, self.status, self.uncertain = category, status, uncertain
        super().__init__(f"GitHub operation failed: {category}; status={status}; outcome_unknown={uncertain}")


def failure_category(status, body, stderr):
    errors = body.get("errors", []) if isinstance(body, dict) else []
    types = {item.get("type") for item in errors if isinstance(item, dict)}
    evidence = (stderr + " " + str(body.get("message", "") if isinstance(body, dict) else "")).lower()
    if status == 429 or "RATE_LIMITED" in types or "rate limit" in evidence:
        return "throttling"
    if status == 401 or "UNAUTHORIZED" in types or "gh auth login" in evidence:
        return "authentication"
    if status == 403 or "FORBIDDEN" in types:
        return "authorization"
    if status == 404:
        return "missing_or_hidden"
    if status == 409:
        return "conflict"
    if any(word in evidence for word in ("proxyconnect", "dial tcp", "could not resolve", "timed out", "connection refused")):
        return "network"
    return "api"


class GitHub:
    def __init__(self, host="github.com", token_variable=None):
        self.host, self.token_variable = host, token_variable

    def request(self, endpoint, method="GET", payload=None, mutating=None, headers=False):
        executable = shutil.which("gh")
        if not executable:
            raise GitHubFailure("missing_tool")
        changes = method != "GET" if mutating is None else mutating
        argv = [executable, "api", "--hostname", self.host, "--method", method, endpoint]
        if headers:
            argv.append("--include")
        if payload is not None:
            argv.extend(["--input", "-"])
        environment = os.environ.copy()
        environment.pop("GH_DEBUG", None)
        if self.token_variable:
            token = environment.get(self.token_variable)
            if not token:
                raise GitHubFailure("missing_credential")
            environment["GH_TOKEN" if self.host == "github.com" else "GH_ENTERPRISE_TOKEN"] = token
        try:
            result = subprocess.run(
                argv, input=json.dumps(payload) if payload is not None else None,
                text=True, encoding="utf-8", capture_output=True, env=environment,
                timeout=45, shell=False,
            )
        except FileNotFoundError:
            raise GitHubFailure("missing_tool") from None
        except subprocess.TimeoutExpired:
            raise GitHubFailure("network", uncertain=changes) from None
        output, response_headers = result.stdout.replace("\r\n", "\n"), ""
        if headers and output.startswith("HTTP/"):
            response_headers, _, output = output.partition("\n\n")
        try:
            body = json.loads(output) if output.strip() else {}
        except ValueError:
            raise GitHubFailure("api", uncertain=changes) from None
        status_match = re.search(r"HTTP (\d{3})", result.stderr)
        status = int(status_match[1]) if status_match else None
        has_errors = isinstance(body, dict) and bool(body.get("errors"))
        if result.returncode or has_errors:
            category = failure_category(status, body, result.stderr)
            raise GitHubFailure(category, status, changes and (category == "network" or has_errors))
        return (body, response_headers) if headers else body

    def graphql(self, query, variables=None, write=False):
        return self.request("graphql", "POST", {"query": query, "variables": variables or {}}, mutating=write)["data"]


SNAPSHOT = """query($id:ID!){node(id:$id){... on ProjectV2{
 id title public owner{... on User{login}}
 repositories(first:20){nodes{id nameWithOwner} pageInfo{hasNextPage}}
 fields(first:100){nodes{__typename ... on ProjectV2Field{id name}
 ... on ProjectV2SingleSelectField{id name options{id name color description}}} pageInfo{hasNextPage}}
 views(first:100){nodes{id name layout configuration{visibleFields(first:100){nodes{
 ... on ProjectV2Field{id name} ... on ProjectV2SingleSelectField{id name}}}}} pageInfo{hasNextPage}}
 items(first:100){nodes{id content{... on Issue{id repository{id}}}
 fieldValues(first:100){nodes{... on ProjectV2ItemFieldSingleSelectValue{optionId field{
 ... on ProjectV2SingleSelectField{id name}}}}}} pageInfo{hasNextPage}}
}}}"""


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
        project = cls.gh.graphql("mutation($input:CreateProjectV2Input!){createProjectV2(input:$input){projectV2{id url}}}", {"input": {"ownerId": owner_id, "title": cls.name}}, write=True)["createProjectV2"]["projectV2"]
        cls.project_id = project["id"]
        cls.state.update(project_id=cls.project_id, project_url=project["url"], phase="project_created")
        cls.save_state()
        cls.gh.graphql("mutation($input:UpdateProjectV2Input!){updateProjectV2(input:$input){projectV2{id public}}}", {"input": {"projectId": cls.project_id, "public": False}}, write=True)
        cls.gh.graphql("mutation($input:LinkProjectV2ToRepositoryInput!){linkProjectV2ToRepository(input:$input){repository{id}}}", {"input": {"projectId": cls.project_id, "repositoryId": cls.repo_id}}, write=True)
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

    def snapshot(self):
        project = self.gh.graphql(SNAPSHOT, {"id": self.project_id})["node"]
        for connection in ("repositories", "fields", "views", "items"):
            self.assertFalse(project[connection]["pageInfo"]["hasNextPage"], "Fixture exceeded the test page bound")
        return project

    def label(self, name, color="1D76DB", description="Disposable test label"):
        path = f"repos/{self.repo}/labels/{quote(name, safe='')}"
        try:
            existing = self.gh.request(path)
        except GitHubFailure as error:
            if error.status != 404:
                raise
            return self.gh.request(f"repos/{self.repo}/labels", "POST", {"name": name, "color": color, "description": description})
        if existing["color"].lower() == color.lower() and (existing["description"] or "") == description:
            return existing
        return self.gh.request(path, "PATCH", {"color": color, "description": description})

    def priority_and_view(self):
        project = self.snapshot()
        fields = project["fields"]["nodes"]
        matching = [field for field in fields if field.get("name") == "Priority"]
        self.assertLessEqual(len(matching), 1)
        if not matching:
            self.gh.graphql("mutation($input:CreateProjectV2FieldInput!){createProjectV2Field(input:$input){projectV2Field{... on ProjectV2SingleSelectField{id}}}}", {"input": {"projectId": self.project_id, "name": "Priority", "dataType": "SINGLE_SELECT", "singleSelectOptions": [{"name": name, "color": "BLUE", "description": "Disposable priority"} for name in ("P0", "P1", "P2")]}}, write=True)
            fields = self.snapshot()["fields"]["nodes"]
        priority = next(field for field in fields if field.get("name") == "Priority")
        self.assertEqual(priority["__typename"], "ProjectV2SingleSelectField")
        status = next(field for field in fields if field.get("name") == "Status")
        title = next(field for field in fields if field.get("name") == "Title")
        views = [view for view in project["views"]["nodes"] if view["name"] == "Test board"]
        self.assertLessEqual(len(views), 1)
        if not views:
            self.gh.graphql("mutation($input:CreateProjectV2ViewInput!){createProjectV2View(input:$input){projectV2View{id}}}", {"input": {"projectId": self.project_id, "name": "Test board", "layout": "BOARD_LAYOUT", "configuration": {"visibleFieldIds": [title["id"], status["id"], priority["id"]]}}}, write=True)
        return priority, status

    def content(self, path, value):
        endpoint = f"repos/{self.repo}/contents/{path}"
        data = {"message": "test: publish workflow asset", "content": base64.b64encode(value).decode("ascii")}
        try:
            existing = self.gh.request(endpoint)
        except GitHubFailure as error:
            if error.status != 404:
                raise
        else:
            if base64.b64decode(existing["content"]) == value:
                return existing["sha"]
            data["sha"] = existing["sha"]
        return self.gh.request(endpoint, "PUT", data)["content"]["sha"]

    def populated_issue(self, status, priority):
        self.label("type:bug")
        issue = self.gh.request(f"repos/{self.repo}/issues", "POST", {"title": "Disposable verification issue", "body": "Fixture data only.", "labels": ["type:bug"]})
        item = self.gh.graphql("mutation($input:AddProjectV2ItemByIdInput!){addProjectV2ItemById(input:$input){item{id}}}", {"input": {"projectId": self.project_id, "contentId": issue["node_id"]}}, write=True)["addProjectV2ItemById"]["item"]
        for field in (status, priority):
            self.gh.graphql("mutation($input:UpdateProjectV2ItemFieldValueInput!){updateProjectV2ItemFieldValue(input:$input){projectV2Item{id}}}", {"input": {"projectId": self.project_id, "itemId": item["id"], "fieldId": field["id"], "value": {"singleSelectOptionId": field["options"][0]["id"]}}}, write=True)
        return issue, item

    def test_00_empty_repository(self):
        repository = self.gh.request(f"repos/{self.repo}")
        self.assertTrue(repository["private"])
        self.assertEqual(repository["size"], 0)
        project = self.snapshot()
        self.assertFalse(project["public"])
        self.assertIn(self.repo_id, {repo["id"] for repo in project["repositories"]["nodes"]})
        self.assertEqual(sum(field.get("name") == "Status" for field in project["fields"]["nodes"]), 1)

    def test_10_existing_configuration(self):
        kept = self.label("keep-me", "123456", "Unrelated configuration")
        existing = self.gh.request(f"repos/{self.repo}/labels/bug")
        updated = self.label("bug", "654321", "Updated description")
        self.assertEqual(existing["id"], updated["id"])
        self.assertEqual(kept["id"], self.label("keep-me", "123456", "Unrelated configuration")["id"])
        self.assertEqual(self.gh.request(f"repos/{self.repo}/labels/bug")["color"], "654321")

    def test_20_missing_write_permission(self):
        if not os.environ.get("REPO_SETUP_READ_ONLY_TOKEN"):
            self.skipTest("No restricted fixture-readable credential supplied")
        restricted = GitHub(HOST, "REPO_SETUP_READ_ONLY_TOKEN")
        self.assertEqual(restricted.request(f"repos/{self.repo}")["node_id"], self.repo_id)
        with self.assertRaises(GitHubFailure) as failure:
            restricted.request(f"repos/{self.repo}/labels", "POST", {"name": "denied-write", "color": "123456"})
        self.assertEqual(failure.exception.category, "authorization")
        with self.assertRaises(GitHubFailure) as missing:
            self.gh.request(f"repos/{self.repo}/labels/denied-write")
        self.assertEqual(missing.exception.status, 404)

    def test_30_interrupted_execution(self):
        created = None
        with self.assertRaises(GitHubFailure):
            created = self.label("resume-after-write")
            raise GitHubFailure("network", uncertain=True)  # Lost response after a real write.
        resumed = self.label("resume-after-write")
        self.assertEqual(created["id"], resumed["id"])
        labels = self.gh.request(f"repos/{self.repo}/labels?per_page=100")
        self.assertEqual(sum(label["name"] == "resume-after-write" for label in labels), 1)

    def test_40_repeated_execution(self):
        def apply_fixture_recipe():
            label = self.label("type:task")
            priority, _ = self.priority_and_view()
            sha = self.content(".github/pull_request_template.md", (ROOT / "assets/pull_request_template.md").read_bytes())
            views = [view["id"] for view in self.snapshot()["views"]["nodes"] if view["name"] == "Test board"]
            return label["id"], priority["id"], sha, views
        first, second = apply_fixture_recipe(), apply_fixture_recipe()
        self.assertEqual(first, second)
        self.assertEqual(len(second[3]), 1)

    def test_50_creation_and_read_back(self):
        priority, status = self.priority_and_view()
        issue, item = self.populated_issue(status, priority)
        project = self.snapshot()
        card = next(card for card in project["items"]["nodes"] if card["id"] == item["id"])
        self.assertEqual(card["content"]["id"], issue["node_id"])
        self.assertEqual(card["content"]["repository"]["id"], self.repo_id)
        values = {value["field"]["id"]: value["optionId"] for value in card["fieldValues"]["nodes"] if "optionId" in value}
        for field in (status, priority):
            self.assertEqual(values[field["id"]], field["options"][0]["id"])
        view = next(view for view in project["views"]["nodes"] if view["name"] == "Test board")
        self.assertEqual(view["layout"], "BOARD_LAYOUT")
        self.assertEqual([field["name"] for field in view["configuration"]["visibleFields"]["nodes"]], ["Title", "Status", "Priority"])
        for name in ("task.yml", "bug.yml", "config.yml"):
            value = (ROOT / "assets/issue-templates" / name).read_bytes()
            path = f".github/ISSUE_TEMPLATE/{name}"
            self.content(path, value)
            self.assertEqual(base64.b64decode(self.gh.request(f"repos/{self.repo}/contents/{path}")["content"]), value)

    def test_60_add_status_preserves_assignments(self):
        priority, status = self.priority_and_view()
        self.populated_issue(status, priority)
        project = self.snapshot()
        status = next(field for field in project["fields"]["nodes"] if field.get("name") == "Status")
        def assignments(snapshot):
            return {item["id"]: {value["field"]["id"]: value["optionId"] for value in item["fieldValues"]["nodes"] if "optionId" in value} for item in snapshot["items"]["nodes"]}
        before_values = assignments(project)
        before_ids = {option["name"]: option["id"] for option in status["options"]}
        options = status["options"] + [{"name": "In Review", "color": "PURPLE", "description": "Added without replacing populated options"}]
        self.gh.graphql("mutation($input:UpdateProjectV2FieldInput!){updateProjectV2Field(input:$input){projectV2Field{... on ProjectV2SingleSelectField{id}}}}", {"input": {"fieldId": status["id"], "singleSelectOptions": options}}, write=True)
        after = self.snapshot()
        updated = next(field for field in after["fields"]["nodes"] if field.get("name") == "Status")
        after_ids = {option["name"]: option["id"] for option in updated["options"]}
        self.assertTrue(all(after_ids[name] == option_id for name, option_id in before_ids.items()))
        self.assertIn("In Review", after_ids)
        self.assertEqual(before_values, assignments(after))


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
