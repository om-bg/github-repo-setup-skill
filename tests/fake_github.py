"""Small stateful GitHub boundary for exercising the shipped operations offline."""
from copy import deepcopy
import base64
import hashlib
import re
from urllib.parse import unquote, urlsplit, parse_qs

from runtime import GitHubFailure


class FakeGitHub:
    host = "github.com"

    def __init__(self):
        self.repo = {"node_id": "R_fixture", "default_branch": "main", "owner": {"node_id": "U_fixture", "id": 42, "type": "User"}}
        self.fields = [self.field(name, "ProjectV2Field") for name in ("Title", "Assignees", "Labels")]
        self.fields.append(self.field("Status", options=[self.option("Todo"), self.option("Done")]))
        self.views, self.items, self.labels, self.files = [], [], {}, {}
        self.issues = {1: {"node_id": "I_fixture", "number": 1}}
        self.writes, self.calls, self.counter = [], [], 100
        self.blocked, self.fail_after, self.page_size = False, None, 100
        self.branches, self.pulls = {"main": "initial"}, []
        self.board_payloads = []
        self.ignore_board_grouping = False

    @staticmethod
    def option(name):
        return {"id": "opt_" + name, "name": name, "color": "BLUE", "description": "Existing option"}

    @staticmethod
    def field(name, kind="ProjectV2SingleSelectField", options=None):
        result = {"id": "field_" + name, "databaseId": 1000 + sum(map(ord, name)), "name": name, "__typename": kind}
        if options is not None:
            result["options"] = options
        return result

    def next_id(self):
        self.counter += 1
        return str(self.counter)

    def check(self):
        if self.blocked:
            raise GitHubFailure("network")

    def committed(self, operation):
        self.writes.append(operation)
        if self.fail_after == operation:
            self.fail_after = None
            raise GitHubFailure("network", uncertain=True)

    def request(self, endpoint, method="GET", payload=None, **kwargs):
        self.check()
        self.calls.append((method, endpoint))
        if method == "GET" and endpoint == "repos/example/remote":
            return deepcopy(self.repo)
        if "/issues/" in endpoint and method == "GET":
            return deepcopy(self.issues[int(endpoint.rsplit("/", 1)[1])])
        if re.fullmatch(r"(users/42|orgs/example)/projectsV2/2/views", endpoint) and method == "POST":
            assert kwargs.get("api_version") == "2026-03-10"
            self.board_payloads.append(deepcopy(payload))
            def fields(ids):
                return [deepcopy(next(field for field in self.fields if field["databaseId"] == value)) for value in ids]
            self.views.append({"id": self.next_id(), "name": payload["name"], "layout": "BOARD_LAYOUT", "filter": payload["filter"],
                               "configuration": {"visibleFields": {"nodes": fields(payload["visible_fields"]), "pageInfo": {"hasNextPage": False}}},
                               "verticalGroupByFields": {"nodes": [] if self.ignore_board_grouping else fields(payload["vertical_group_by"]), "pageInfo": {"hasNextPage": False}}})
            self.committed("createBoardREST")
            return {"value": {"node_id": self.views[-1]["id"]}}
        if "/git/ref/heads/" in endpoint and method == "GET":
            branch = unquote(endpoint.split("/git/ref/heads/", 1)[1])
            if branch not in self.branches:
                raise GitHubFailure("missing_or_hidden", 404)
            return {"object": {"sha": self.branches[branch]}}
        if endpoint.endswith("/git/refs") and method == "POST":
            branch = payload["ref"].removeprefix("refs/heads/")
            assert branch not in self.branches
            source = next(name for name, sha in self.branches.items() if sha == payload["sha"])
            for (name, path), value in list(self.files.items()):
                if name == source:
                    self.files[(branch, path)] = deepcopy(value)
            self.branches[branch] = payload["sha"]
            self.committed("branch")
            return {"ref": payload["ref"]}
        if "/pulls" in endpoint:
            if method == "POST":
                pull = {"number": len(self.pulls) + 1, "state": "open", "html_url": "https://github.com/example/remote/pull/1",
                        "head": {"ref": payload["head"], "repo": {"node_id": self.repo["node_id"]}},
                        "base": {"ref": payload["base"], "repo": {"node_id": self.repo["node_id"]}}}
                self.pulls.append(pull)
                self.committed("pull")
                return deepcopy(pull)
            if "?" in endpoint:
                query = parse_qs(urlsplit(endpoint).query)
                return deepcopy([pull for pull in self.pulls if pull["state"] == "open" and "example:" + pull["head"]["ref"] == query["head"][0] and pull["base"]["ref"] == query["base"][0]])
            return deepcopy(next(pull for pull in self.pulls if pull["number"] == int(endpoint.rsplit("/", 1)[1])))
        if "/labels" in endpoint:
            name = unquote(endpoint.rsplit("/", 1)[1]) if "/labels/" in endpoint else payload["name"]
            if method == "GET":
                if name.casefold() not in self.labels:
                    raise GitHubFailure("missing_or_hidden", 404)
                return deepcopy(self.labels[name.casefold()])
            value = self.labels.setdefault(name.casefold(), {"id": self.next_id(), "name": name})
            value.update(payload)
            self.committed("label")
            return deepcopy(value)
        if "/contents/" in endpoint:
            parsed = urlsplit(endpoint)
            branch = parse_qs(parsed.query).get("ref", ["main"])[0] if method == "GET" else payload.get("branch", "main")
            assert branch in self.branches
            key = (branch, parsed.path)
            if method == "GET":
                if key not in self.files:
                    raise GitHubFailure("missing_or_hidden", 404)
                return deepcopy(self.files[key])
            if key in self.files:
                assert payload["sha"] == self.files[key]["sha"]
            value = {"sha": hashlib.sha256(base64.b64decode(payload["content"])).hexdigest(), "content": payload["content"]}
            self.files[key] = value
            self.branches[branch] = self.next_id()
            self.committed("content")
            return {"content": deepcopy(value)}
        raise AssertionError("Unexpected test request")

    def page(self, values, cursor):
        start = int(cursor or 0)
        end = min(start + self.page_size, len(values))
        return {"nodes": deepcopy(values[start:end]), "pageInfo": {"hasNextPage": end < len(values), "endCursor": str(end)}}

    def graphql(self, query, variables=None, write=False):
        self.check()
        variables = variables or {}
        if not write:
            if "projectV2(number:" in query:
                return {"node": {"projectV2": {"id": "P_fixture", "title": "Fixture"}}}
            for name in ("fields", "views", "items", "repositories"):
                if name + "(first:" in query:
                    values = [self.repo | {"id": self.repo["node_id"]}] if name == "repositories" else getattr(self, name)
                    return {"node": {name: self.page(values, variables.get("after"))}}
            raise AssertionError("Unexpected test query")
        operation = re.search(r"\{(\w+)\(input:", query)[1]
        data = variables["input"]
        if operation == "createProjectV2Field":
            field = self.field(data["name"], options=[dict(option, id=self.next_id()) for option in data["singleSelectOptions"]])
            self.fields.append(field)
        elif operation == "updateProjectV2Field":
            field = next(field for field in self.fields if field["id"] == data["fieldId"])
            field["options"] = [dict(option, id=option.get("id") or self.next_id()) for option in data["singleSelectOptions"]]
            retained = {option["id"] for option in field["options"]}
            for item in self.items:
                item["fieldValues"]["nodes"] = [value for value in item["fieldValues"]["nodes"] if value["field"]["id"] != field["id"] or value["optionId"] in retained]
        elif operation == "updateProjectV2View":
            view = next(view for view in self.views if view["id"] == data["viewId"])
            view.update({key: data[key] for key in ("layout", "filter") if key in data})
            selected = [deepcopy(next(field for field in self.fields if field["id"] == field_id)) for field_id in data["configuration"]["visibleFieldIds"]]
            view["configuration"] = {"visibleFields": {"nodes": selected, "pageInfo": {"hasNextPage": False}}}
        elif operation == "addProjectV2ItemById":
            item = {"id": self.next_id(), "isArchived": False, "content": {"id": data["contentId"], "repository": {"id": self.repo["node_id"]}}, "fieldValues": {"nodes": [], "pageInfo": {"hasNextPage": False}}}
            self.items.append(item)
        elif operation == "updateProjectV2ItemFieldValue":
            item = next(item for item in self.items if item["id"] == data["itemId"])
            values = item["fieldValues"]["nodes"]
            values[:] = [value for value in values if value["field"]["id"] != data["fieldId"]]
            values.append({"field": {"id": data["fieldId"]}, "optionId": data["value"]["singleSelectOptionId"]})
        else:
            raise AssertionError("Unexpected test mutation")
        self.committed(operation)
        if operation == "addProjectV2ItemById":
            return {operation: {"item": {"id": item["id"]}}}
        return {operation: {}}
