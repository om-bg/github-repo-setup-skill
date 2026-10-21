"""Shared GitHub operations for the installed skill and maintainer tests."""

import argparse
import base64
import json
import os
from pathlib import Path
import re
import shutil
import subprocess
import sys
from urllib.parse import quote

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

    def request(self, endpoint, method="GET", payload=None, mutating=None, headers=False, api_version=None):
        executable = shutil.which("gh")
        if not executable:
            raise GitHubFailure("missing_tool")
        changes = method != "GET" if mutating is None else mutating
        argv = [executable, "api", "--hostname", self.host, "--method", method, endpoint]
        if api_version:
            argv.extend(["-H", f"X-GitHub-Api-Version: {api_version}"])
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


FIELD = """__typename ... on ProjectV2Field{id name databaseId}
 ... on ProjectV2SingleSelectField{id name databaseId options{id name color description}}
 ... on ProjectV2IterationField{id name databaseId} ... on ProjectV2MultiSelectField{id name databaseId}"""
VIEW = """id name layout filter
 configuration{visibleFields(first:100){nodes{FIELD} pageInfo{hasNextPage}}}
 verticalGroupByFields(first:100){nodes{FIELD} pageInfo{hasNextPage}}""".replace("FIELD", FIELD)
ITEM = """id isArchived content{... on Issue{id repository{id}}}
 fieldValues(first:100){nodes{... on ProjectV2ItemFieldSingleSelectValue{
 optionId field{... on ProjectV2SingleSelectField{id name}}}} pageInfo{hasNextPage}}"""


def require(condition, category="conflict"):
    if not condition:
        raise GitHubFailure(category)


def unique(values, name):
    matching = [value for value in values if value.get("name") == name]
    require(len(matching) <= 1, "ambiguous_resource")
    return matching[0] if matching else None


class Workflow:
    """Explicit remote target, additive field plans, and read-back-verified writes.

    No YAML loading, auth changes, resource deletion, or automatic rollback.
    """

    def __init__(self, github, repository, project_number=None):
        require(bool(re.fullmatch(r"[A-Za-z0-9_.-]+/[A-Za-z0-9_.-]+", repository)), "invalid_target")
        require(all(part not in {".", ".."} for part in repository.split("/")), "invalid_target")
        require(project_number is None or isinstance(project_number, int) and project_number > 0, "invalid_target")
        self.gh, self.repo, self.number = github, repository, project_number
        self.repository = self.gh.request(f"repos/{repository}")
        self.project_id = None
        if project_number is None:
            return
        owner = self.repository["owner"]
        project = self.gh.graphql("""query($id:ID!,$number:Int!){node(id:$id){
         ... on User{projectV2(number:$number){id title}}
         ... on Organization{projectV2(number:$number){id title}}}}""",
         {"id": owner["node_id"], "number": project_number})["node"]
        require(bool(project and project.get("projectV2")), "missing_or_hidden")
        self.project_id = project["projectV2"]["id"]

    @property
    def target(self):
        return {"host": self.gh.host, "repository": self.repo, "repository_id": self.repository["node_id"], "project_id": self.project_id}

    def connection(self, name, selection):
        # Connection names/selections are internal constants, never config text.
        require(self.project_id is not None, "missing_project")
        require(name in {"fields", "views", "items", "repositories"}, "api")
        arguments = "first:100,after:$after"
        if name == "items":
            arguments += ",archivedStates:[ARCHIVED,NOT_ARCHIVED]"
        query = "query($id:ID!,$after:String){node(id:$id){... on ProjectV2{" + name + "(" + arguments + "){nodes{" + selection + "} pageInfo{hasNextPage endCursor}}}}}"
        results, cursor, seen = [], None, set()
        while True:
            node = self.gh.graphql(query, {"id": self.project_id, "after": cursor})["node"]
            require(node is not None, "missing_or_hidden")
            page = node[name]
            for value in page["nodes"]:
                if value is not None:
                    results.append(value)
            if not page["pageInfo"]["hasNextPage"]:
                return results
            cursor = page["pageInfo"]["endCursor"]
            require(bool(cursor) and cursor not in seen, "incomplete_inventory")
            seen.add(cursor)

    def fields(self):
        return self.connection("fields", FIELD)

    def views(self):
        views = self.connection("views", VIEW)
        for view in views:
            require(not view["configuration"]["visibleFields"]["pageInfo"]["hasNextPage"], "incomplete_inventory")
            require(not view["verticalGroupByFields"]["pageInfo"]["hasNextPage"], "incomplete_inventory")
        return views

    def items(self):
        items = self.connection("items", ITEM)
        require(all(not item["fieldValues"]["pageInfo"]["hasNextPage"] for item in items), "incomplete_inventory")
        return items

    def assignments(self):
        return {item["id"]: {value["field"]["id"]: value["optionId"] for value in item["fieldValues"]["nodes"] if "optionId" in value} for item in self.items()}

    def audit(self):
        return {"target": self.target, "linked": self.repository["node_id"] in {repo["id"] for repo in self.connection("repositories", "id")}, "fields": self.fields(), "views": self.views(), "items": self.items()}

    def plan_field(self, name, desired):
        require(name in {"Status", "Priority"}, "invalid_input")
        require(bool(desired) and all(isinstance(value, str) and value.strip() for value in desired), "invalid_input")
        require(len(set(desired)) == len(desired), "invalid_input")
        before = unique(self.fields(), name)
        require(before is not None or name == "Priority", "missing_status")
        require(before is None or before["__typename"] == "ProjectV2SingleSelectField", "field_type_conflict")
        options = list(before["options"]) if before else []
        for label in desired:
            if not any(option["name"] == label for option in options):
                options.append({"name": label, "color": "GRAY", "description": ""})
        return {"kind": "field", "target": self.target, "name": name, "desired": desired, "before": before, "options": options, "assignments": self.assignments()}

    def verify_field(self, plan):
        require(plan["target"] == self.target, "invalid_target")
        actual = unique(self.fields(), plan["name"])
        old = plan["before"]
        if not actual or actual["__typename"] != "ProjectV2SingleSelectField":
            return False
        by_name = {option["name"]: option for option in actual["options"]}
        if not all(name in by_name for name in plan["desired"]):
            return False
        if old and (actual["id"] != old["id"] or any(by_name.get(option["name"]) != option for option in old["options"])):
            return False
        current = self.assignments()
        return all(current.get(item_id) == values for item_id, values in plan["assignments"].items())

    def apply_field(self, plan, approved=False):
        require(approved, "approval_required")
        require(plan.get("kind") == "field" and plan.get("target") == self.target, "invalid_target")
        # Recompute the payload: plan input is data, not authority to submit arbitrary IDs.
        current = self.plan_field(plan["name"], plan["desired"])
        if self.verify_field(plan):
            return {"changed": False, "verified": True}
        require(current["before"] == plan["before"] and current["assignments"] == plan["assignments"], "state_drift")
        if current["before"]:
            self.gh.graphql("mutation($input:UpdateProjectV2FieldInput!){updateProjectV2Field(input:$input){projectV2Field{... on ProjectV2SingleSelectField{id}}}}", {"input": {"fieldId": current["before"]["id"], "singleSelectOptions": current["options"]}}, write=True)
        else:
            self.gh.graphql("mutation($input:CreateProjectV2FieldInput!){createProjectV2Field(input:$input){projectV2Field{... on ProjectV2SingleSelectField{id}}}}", {"input": {"projectId": self.project_id, "name": plan["name"], "dataType": "SINGLE_SELECT", "singleSelectOptions": current["options"]}}, write=True)
        require(self.verify_field(plan), "verification")
        return {"changed": True, "verified": True}

    def plan_board(self, name, visible):
        require(isinstance(name, str) and bool(name.strip()), "invalid_input")
        require(bool(visible) and len(set(visible)) == len(visible), "invalid_input")
        fields = self.fields()
        status = unique(fields, "Status")
        require(status and status["__typename"] == "ProjectV2SingleSelectField", "missing_status")
        selected = [unique(fields, value) for value in visible]
        require(all(selected), "missing_field")
        before = unique(self.views(), name)
        return {"kind": "board", "target": self.target, "name": name, "visible": visible, "before": before, "field_ids": [field["id"] for field in selected], "filter": before["filter"] if before else f"repo:{self.repo}"}

    def verify_board(self, plan):
        require(plan["target"] == self.target, "invalid_target")
        view = unique(self.views(), plan["name"])
        status = unique(self.fields(), "Status")
        checks = {"layout": bool(view and view["layout"] == "BOARD_LAYOUT"), "filter": bool(view and view["filter"] == plan["filter"]), "fields": bool(view and [field["id"] for field in view["configuration"]["visibleFields"]["nodes"]] == plan["field_ids"]), "grouping": bool(view and status and [field["id"] for field in view["verticalGroupByFields"]["nodes"]] == [status["id"]]), "repository_link": self.repository["node_id"] in {repo["id"] for repo in self.connection("repositories", "id")}}
        owner_type = "orgs" if self.repository["owner"]["type"] == "Organization" else "users"
        project_url = f"https://{self.gh.host}/{owner_type}/{self.repo.split('/')[0]}/projects/{self.number}"
        manual = [] if checks["grouping"] else [f"Open {project_url}, select view {plan['name']!r}, and set its column field to Status. The GraphQL update input does not expose a grouping setter; keep the existing view, filter, and cards."]
        if not checks["repository_link"]:
            manual.append("Link the selected repository to this project through an authorized project-link operation.")
        return {"checks": checks, "verified": all(checks.values()), "manual": manual}

    def apply_board(self, plan, approved=False):
        require(approved, "approval_required")
        require(plan.get("kind") == "board" and plan.get("target") == self.target, "invalid_target")
        current = self.plan_board(plan["name"], plan["visible"])
        require(current["field_ids"] == plan["field_ids"] and current["filter"] == plan["filter"], "state_drift")
        before = current["before"]
        verification = self.verify_board(plan)
        if all(verification["checks"][key] for key in ("layout", "filter", "fields")):
            return {"changed": False, **verification}
        if plan["before"] is not None:
            require(before == plan["before"], "state_drift")
        elif before:
            # A prior create may have succeeded before its filter update failed.
            require(before["layout"] == "BOARD_LAYOUT" and [field["id"] for field in before["configuration"]["visibleFields"]["nodes"]] == plan["field_ids"], "state_drift")
        if not before:
            fields = self.fields()
            selected = [unique(fields, name) for name in plan["visible"]]
            status = unique(fields, "Status")
            # REST expects numeric field database IDs, never GraphQL node/option IDs.
            require(all(field and type(field.get("databaseId")) is int and field["databaseId"] > 0 for field in [*selected, status]), "missing_field_id")
            owner = self.repository["owner"]
            if owner["type"] == "Organization":
                owner_path = "orgs/" + self.repo.split("/")[0]
            else:
                require(owner["type"] == "User" and type(owner.get("id")) is int and owner["id"] > 0, "invalid_target")
                owner_path = f"users/{owner['id']}"
            self.gh.request(f"{owner_path}/projectsV2/{self.number}/views", "POST", {
                "name": plan["name"], "layout": "board", "filter": plan["filter"],
                "visible_fields": [field["databaseId"] for field in selected],
                "vertical_group_by": [status["databaseId"]],
            }, api_version="2026-03-10")
            return {"changed": True, **self.verify_board(plan)}
        self.gh.graphql("mutation($input:UpdateProjectV2ViewInput!){updateProjectV2View(input:$input){projectV2View{id}}}", {"input": {"viewId": before["id"], "layout": "BOARD_LAYOUT", "filter": plan["filter"], "configuration": {"visibleFieldIds": plan["field_ids"]}}}, write=True)
        return {"changed": True, **self.verify_board(plan)}

    def associate(self, issue_number, values, approved=False):
        require(approved, "approval_required")
        require(isinstance(issue_number, int) and issue_number > 0, "invalid_input")
        issue = self.gh.request(f"repos/{self.repo}/issues/{issue_number}")
        require("pull_request" not in issue, "invalid_input")
        fields, requested = self.fields(), {}
        for name, value in values.items():
            field = unique(fields, name)
            require(field and field["__typename"] == "ProjectV2SingleSelectField", "field_type_conflict")
            option = unique(field["options"], value)
            require(option is not None, "missing_option")
            requested[field["id"]] = option["id"]
        matches = [item for item in self.items() if item["content"] and item["content"].get("id") == issue["node_id"]]
        require(len(matches) <= 1, "ambiguous_resource")
        require(not matches or not matches[0]["isArchived"], "archived_item")
        if matches:
            item_id = matches[0]["id"]
        else:
            item_id = self.gh.graphql("mutation($input:AddProjectV2ItemByIdInput!){addProjectV2ItemById(input:$input){item{id}}}", {"input": {"projectId": self.project_id, "contentId": issue["node_id"]}}, write=True)["addProjectV2ItemById"]["item"]["id"]
        current = self.assignments().get(item_id, {})
        for field_id, option_id in requested.items():
            if current.get(field_id) != option_id:
                self.gh.graphql("mutation($input:UpdateProjectV2ItemFieldValueInput!){updateProjectV2ItemFieldValue(input:$input){projectV2Item{id}}}", {"input": {"projectId": self.project_id, "itemId": item_id, "fieldId": field_id, "value": {"singleSelectOptionId": option_id}}}, write=True)
        item = next((item for item in self.items() if item["id"] == item_id), None)
        require(item and item["content"]["id"] == issue["node_id"] and item["content"]["repository"]["id"] == self.repository["node_id"], "verification")
        actual = self.assignments()[item_id]
        require(all(actual.get(key) == value for key, value in requested.items()), "verification")
        return {"item_id": item_id, "issue_id": issue["node_id"], "verified": True}

    def label(self, name, color, description, approved=False):
        require(approved, "approval_required")
        path = f"repos/{self.repo}/labels/{quote(name, safe='')}"
        try:
            existing = self.gh.request(path)
        except GitHubFailure as error:
            if error.status != 404:
                raise
            self.gh.request(f"repos/{self.repo}/labels", "POST", {"name": name, "color": color, "description": description})
        else:
            if existing["color"].lower() != color.lower() or (existing["description"] or "") != description:
                self.gh.request(path, "PATCH", {"color": color, "description": description})
        actual = self.gh.request(path)
        require(actual["color"].lower() == color.lower() and (actual["description"] or "") == description, "verification")
        return actual

    @staticmethod
    def template_path(path):
        require(bool(re.fullmatch(r"\.github/(pull_request_template\.(md|txt)|ISSUE_TEMPLATE/[A-Za-z0-9_.-]+\.(yml|yaml|md))", path)) and all(part.lower() != "secret.md" for part in path.split("/")), "invalid_path")

    def content(self, path, value, approved=False, *, branch=None):
        require(approved, "approval_required")
        self.template_path(path)
        require(branch is None or isinstance(branch, str) and bool(branch), "invalid_input")
        endpoint = f"repos/{self.repo}/contents/{path}"
        read_endpoint = endpoint + ("?ref=" + quote(branch, safe="") if branch is not None else "")
        data = {"message": "chore: update repository workflow", "content": base64.b64encode(value).decode("ascii")}
        if branch is not None:
            data["branch"] = branch
        try:
            existing = self.gh.request(read_endpoint)
        except GitHubFailure as error:
            if error.status != 404:
                raise
        else:
            if base64.b64decode(existing["content"]) == value:
                return existing["sha"]
            data["sha"] = existing["sha"]
        self.gh.request(endpoint, "PUT", data)
        actual = self.gh.request(read_endpoint)
        require(base64.b64decode(actual["content"]) == value, "verification")
        return actual["sha"]

    def publish_templates(self, files, route, *, branch=None, base=None, title=None, body=None, approved=False):
        """Publish selected template bytes; branch/PR routes never write the base."""
        require(approved, "approval_required")
        require(route in {"direct", "branch", "pr"} and bool(files), "invalid_input")
        for path, value in files.items():
            self.template_path(path)
            require(isinstance(value, bytes), "invalid_input")
        base = base or self.repository.get("default_branch")
        require(isinstance(base, str) and bool(base), "missing_base")
        target = base if route == "direct" else branch
        require(isinstance(target, str) and bool(target), "missing_branch")
        if route != "direct":
            require(target != base and target != self.repository.get("default_branch"), "invalid_target")
            if route == "pr":
                require(isinstance(title, str) and bool(title.strip()) and isinstance(body, str), "invalid_input")
            ref = f"repos/{self.repo}/git/ref/heads/" + quote(target, safe="")
            try:
                self.gh.request(ref)
            except GitHubFailure as error:
                if error.status != 404:
                    raise
                source = self.gh.request(f"repos/{self.repo}/git/ref/heads/" + quote(base, safe=""))
                self.gh.request(f"repos/{self.repo}/git/refs", "POST", {"ref": "refs/heads/" + target, "sha": source["object"]["sha"]})
                self.gh.request(ref)
        for path, value in files.items():
            self.content(path, value, approved=True, branch=target)
        result = {"route": route, "branch": target, "base": base, "verified": True,
                  "active_on_default_branch": target == self.repository.get("default_branch")}
        if route == "pr":
            head = self.repo.split("/")[0] + ":" + target
            endpoint = f"repos/{self.repo}/pulls"
            pulls = self.gh.request(endpoint + "?state=open&head=" + quote(head, safe="") + "&base=" + quote(base, safe="") + "&per_page=100")
            require(len(pulls) <= 1, "ambiguous_resource")
            if pulls:
                pull = pulls[0]
            else:
                pull = self.gh.request(endpoint, "POST", {"head": target, "base": base, "title": title, "body": body})
            actual = self.gh.request(endpoint + f"/{pull['number']}")
            require(actual["state"] == "open" and actual["head"]["ref"] == target and actual["base"]["ref"] == base
                    and actual["head"]["repo"]["node_id"] == self.repository["node_id"]
                    and actual["base"]["repo"]["node_id"] == self.repository["node_id"], "verification")
            result["pull_request"] = actual["html_url"]
        return result


def main():
    parser = argparse.ArgumentParser(description="Explicit-target Projects V2 operations; review plans before approved writes.")
    parser.add_argument("mode", choices=["audit", "plan-field", "apply-field", "verify-field", "plan-board", "apply-board", "verify-board", "associate"])
    parser.add_argument("--repo", required=True, help="OWNER/REPO; never inferred from the current checkout")
    parser.add_argument("--project", required=True, type=int)
    parser.add_argument("--host", default="github.com")
    parser.add_argument("--name")
    parser.add_argument("--options", nargs="+")
    parser.add_argument("--visible", nargs="+", default=["Title", "Assignees", "Status", "Priority", "Labels"])
    parser.add_argument("--plan", type=Path)
    parser.add_argument("--approved", action="store_true", help="The user has approved this concrete change; not a substitute for host execution approval")
    parser.add_argument("--issue", type=int)
    parser.add_argument("--status")
    parser.add_argument("--priority")
    args = parser.parse_args()
    try:
        if args.mode.startswith("apply-") or args.mode == "associate":
            require(args.approved, "approval_required")
        workflow = Workflow(GitHub(args.host), args.repo, args.project)
        if args.mode == "audit":
            result = workflow.audit()
        elif args.mode == "plan-field":
            result = workflow.plan_field(args.name, args.options or [])
        elif args.mode == "plan-board":
            result = workflow.plan_board(args.name, args.visible)
        elif args.mode == "associate":
            values = {name: value for name, value in {"Status": args.status, "Priority": args.priority}.items() if value is not None}
            result = workflow.associate(args.issue, values, approved=args.approved)
        else:
            require(args.plan is not None, "missing_plan")
            plan = json.loads(args.plan.read_text(encoding="utf-8-sig"))
            method = getattr(workflow, args.mode.replace("-", "_"))
            result = method(plan, approved=True) if args.mode.startswith("apply-") else method(plan)
            if isinstance(result, bool):
                result = {"verified": result}
        print(json.dumps(result, indent=2))
        return 0 if result.get("verified", True) else 2
    except GitHubFailure as error:
        print(json.dumps({"error": error.category, "status": error.status, "outcome_unknown": error.uncertain}), file=sys.stderr)
        return 1
    except (ValueError, TypeError, KeyError, OSError):
        print(json.dumps({"error": "invalid_input_or_capability"}), file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())


