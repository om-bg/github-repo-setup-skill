"""Behavior tests use the shipped implementation against a stateful API boundary."""
from copy import deepcopy
import unittest

from fake_github import FakeGitHub
from runtime import GitHubFailure, Workflow


class WorkflowTests(unittest.TestCase):
    def setUp(self):
        self.api = FakeGitHub()
        self.workflow = Workflow(self.api, "example/remote", 2)

    def configure(self):
        for name, choices in (("Status", ["Backlog", "In Review"]), ("Priority", ["P0", "P1"])):
            self.workflow.apply_field(self.workflow.plan_field(name, choices), approved=True)
        plan = self.workflow.plan_board("Board", ["Title", "Status", "Priority"])
        self.assertTrue(self.workflow.apply_board(plan, approved=True)["verified"])

    def test_fresh_repository_remote_target_and_approval(self):
        self.assertEqual(self.api.calls[0], ("GET", "repos/example/remote"))
        plan = self.workflow.plan_field("Priority", ["P0", "P1"])
        self.assertFalse(self.api.writes)
        with self.assertRaises(GitHubFailure) as failure:
            self.workflow.apply_field(plan)
        self.assertEqual(failure.exception.category, "approval_required")
        self.configure()
        self.assertTrue(self.workflow.audit()["linked"])

    def test_existing_status_and_priority_keep_ids_and_assignments(self):
        self.configure()
        self.workflow.associate(1, {"Status": "Todo", "Priority": "P0"}, approved=True)
        before = deepcopy(self.workflow.assignments())
        for name, additions in (("Status", ["Complete"]), ("Priority", ["P2"])):
            plan = self.workflow.plan_field(name, additions)
            self.workflow.apply_field(plan, approved=True)
            self.assertTrue(self.workflow.verify_field(plan))
        self.assertEqual(before, self.workflow.assignments())
        self.assertEqual(len(self.api.items), 1)

    def test_repository_only_label_work_does_not_require_project_access(self):
        workflow = Workflow(self.api, "example/remote")
        self.assertIsNone(workflow.project_id)
        self.assertEqual(workflow.label("bug", "123456", "Bug", approved=True)["name"], "bug")

    def test_repeated_execution_changes_nothing(self):
        self.configure()
        first = self.workflow.associate(1, {"Status": "Backlog", "Priority": "P1"}, approved=True)
        writes = list(self.api.writes)
        self.configure()
        self.assertEqual(first, self.workflow.associate(1, {"Status": "Backlog", "Priority": "P1"}, approved=True))
        self.assertEqual(writes, self.api.writes)

    def test_partial_field_create_response_is_reconciled(self):
        plan = self.workflow.plan_field("Priority", ["P0"])
        self.api.fail_after = "createProjectV2Field"
        with self.assertRaises(GitHubFailure) as failure:
            self.workflow.apply_field(plan, approved=True)
        self.assertTrue(failure.exception.uncertain)
        self.assertFalse(self.workflow.apply_field(plan, approved=True)["changed"])
        self.assertEqual(sum(field["name"] == "Priority" for field in self.api.fields), 1)

    def test_partial_board_create_response_is_reconciled(self):
        self.workflow.apply_field(self.workflow.plan_field("Priority", ["P0"]), approved=True)
        plan = self.workflow.plan_board("Board", ["Title", "Status", "Priority"])
        self.api.fail_after = "createBoardREST"
        with self.assertRaises(GitHubFailure):
            self.workflow.apply_board(plan, approved=True)
        writes = list(self.api.writes)
        result = self.workflow.apply_board(plan, approved=True)
        self.assertTrue(result["verified"])
        self.assertFalse(result["changed"])
        self.assertEqual(writes, self.api.writes)
        self.assertEqual(len(self.api.views), 1)

    def test_new_board_explicitly_sets_status_columns_with_numeric_ids(self):
        plan = self.workflow.plan_board("Board", ["Title", "Labels"])
        self.assertFalse(self.api.writes)
        result = self.workflow.apply_board(plan, approved=True)
        self.assertTrue(result["verified"])
        self.assertEqual(self.api.board_payloads, [{
            "name": "Board", "layout": "board", "filter": "repo:example/remote",
            "visible_fields": [self.api.fields[0]["databaseId"], self.api.fields[2]["databaseId"]],
            "vertical_group_by": [self.api.fields[3]["databaseId"]],
        }])
        self.assertIn(("POST", "users/42/projectsV2/2/views"), self.api.calls)
        self.assertFalse(self.workflow.apply_board(plan, approved=True)["changed"])
        self.assertEqual(len(self.api.board_payloads), 1)

    def test_new_organization_board_uses_organization_endpoint(self):
        self.api.repo["owner"]["type"] = "Organization"
        workflow = Workflow(self.api, "example/remote", 2)
        result = workflow.apply_board(workflow.plan_board("Board", ["Title"]), approved=True)
        self.assertTrue(result["verified"])
        self.assertIn(("POST", "orgs/example/projectsV2/2/views"), self.api.calls)

    def test_new_board_missing_numeric_field_id_fails_before_write(self):
        plan = self.workflow.plan_board("Board", ["Title"])
        self.api.fields[-1]["databaseId"] = None
        with self.assertRaises(GitHubFailure) as failure:
            self.workflow.apply_board(plan, approved=True)
        self.assertEqual(failure.exception.category, "missing_field_id")
        self.assertFalse(self.api.writes)

    def test_board_creation_read_back_rejects_ignored_column_grouping(self):
        self.api.ignore_board_grouping = True
        result = self.workflow.apply_board(self.workflow.plan_board("Board", ["Title"]), approved=True)
        self.assertFalse(result["verified"])
        self.assertFalse(result["checks"]["grouping"])
        self.assertTrue(result["manual"])

    def test_board_creation_requires_approval(self):
        with self.assertRaises(GitHubFailure) as failure:
            self.workflow.apply_board(self.workflow.plan_board("Board", ["Title"]))
        self.assertEqual(failure.exception.category, "approval_required")
        self.assertFalse(self.api.writes)

    def test_template_direct_publication_is_repeatable(self):
        files = {".github/pull_request_template.md": b"Outcome"}
        result = self.workflow.publish_templates(files, "direct", approved=True)
        self.assertTrue(result["active_on_default_branch"])
        writes = list(self.api.writes)
        self.workflow.publish_templates(files, "direct", approved=True)
        self.assertEqual(writes, self.api.writes)

    def test_template_branch_publication_preserves_base_and_branch_specific_sha(self):
        path = ".github/pull_request_template.md"
        self.workflow.content(path, b"Original", approved=True)
        base_sha = self.api.branches["main"]
        files = {path: b"Changed"}
        result = self.workflow.publish_templates(files, "branch", branch="setup/templates", approved=True)
        self.assertFalse(result["active_on_default_branch"])
        self.assertEqual(base_sha, self.api.branches["main"])
        self.assertNotEqual(self.api.files[("main", "repos/example/remote/contents/" + path)], self.api.files[("setup/templates", "repos/example/remote/contents/" + path)])
        self.assertFalse(self.api.pulls)
        writes = list(self.api.writes)
        self.workflow.publish_templates(files, "branch", branch="setup/templates", approved=True)
        self.assertEqual(writes, self.api.writes)

    def test_template_pr_publication_recovers_partial_write_without_duplicates(self):
        files = {".github/ISSUE_TEMPLATE/task.yml": b"name: Task", ".github/pull_request_template.md": b"Outcome"}
        options = {"branch": "setup/templates", "title": "Workflow templates", "body": "Agreed template changes", "approved": True}
        self.api.fail_after = "content"
        with self.assertRaises(GitHubFailure):
            self.workflow.publish_templates(files, "pr", **options)
        self.assertEqual(self.api.branches["main"], "initial")
        self.api.fail_after = "pull"
        with self.assertRaises(GitHubFailure):
            self.workflow.publish_templates(files, "pr", **options)
        writes = list(self.api.writes)
        result = self.workflow.publish_templates(files, "pr", **options)
        self.assertTrue(result["verified"])
        self.assertFalse(result["active_on_default_branch"])
        self.assertEqual(writes, self.api.writes)
        self.assertEqual(len(self.api.pulls), 1)

    def test_template_publication_validates_entire_selection_before_writes(self):
        for files, options, category in (
            ({".github/pull_request_template.md": b"Outcome", "private.md": b"Private"}, {}, "invalid_path"),
            ({".github/pull_request_template.md": b"Outcome"}, {"branch": "main"}, "invalid_target"),
        ):
            with self.subTest(category=category), self.assertRaises(GitHubFailure) as failure:
                self.workflow.publish_templates(files, "branch", approved=True, **options)
            self.assertEqual(failure.exception.category, category)
            self.assertFalse(self.api.writes)

    def test_template_missing_branch_authorization_is_not_treated_as_absence(self):
        from unittest.mock import patch
        original = self.api.request
        def forbidden(endpoint, *args, **kwargs):
            if "/git/ref/" in endpoint:
                raise GitHubFailure("authorization", 403)
            return original(endpoint, *args, **kwargs)
        with patch.object(self.api, "request", side_effect=forbidden), self.assertRaises(GitHubFailure) as failure:
            self.workflow.publish_templates({".github/pull_request_template.md": b"Outcome"}, "branch", branch="setup/templates", approved=True)
        self.assertEqual(failure.exception.category, "authorization")
        self.assertFalse(self.api.writes)

    def test_template_lost_branch_response_reuses_created_branch(self):
        files = {".github/pull_request_template.md": b"Outcome"}
        self.api.fail_after = "branch"
        with self.assertRaises(GitHubFailure):
            self.workflow.publish_templates(files, "branch", branch="setup/templates", approved=True)
        self.assertTrue(self.workflow.publish_templates(files, "branch", branch="setup/templates", approved=True)["verified"])
        self.assertEqual(self.api.writes.count("branch"), 1)
        self.assertEqual(self.api.branches["main"], "initial")

    def test_template_publication_requires_approval(self):
        with self.assertRaises(GitHubFailure) as failure:
            self.workflow.publish_templates({".github/pull_request_template.md": b"Outcome"}, "direct")
        self.assertEqual(failure.exception.category, "approval_required")
        self.assertFalse(self.api.writes)

    def test_blocked_network_has_no_writes_and_can_resume(self):
        self.api.blocked = True
        with self.assertRaises(GitHubFailure) as failure:
            self.workflow.plan_field("Priority", ["P0"])
        self.assertEqual(failure.exception.category, "network")
        self.assertFalse(self.api.writes)
        self.api.blocked = False
        self.configure()

    def test_stale_field_plan_is_rejected(self):
        plan = self.workflow.plan_field("Status", ["Backlog"])
        self.api.fields[-1]["options"].append(self.api.option("Another user's option"))
        with self.assertRaises(GitHubFailure) as failure:
            self.workflow.apply_field(plan, approved=True)
        self.assertEqual(failure.exception.category, "state_drift")
        self.assertFalse(self.api.writes)

    def test_wrong_grouping_is_not_claimed_verified(self):
        self.configure()
        self.api.views[0]["verticalGroupByFields"]["nodes"] = []
        result = self.workflow.verify_board(self.workflow.plan_board("Board", ["Title", "Status", "Priority"]))
        self.assertFalse(result["verified"])
        self.assertFalse(result["checks"]["grouping"])
        self.assertTrue(result["manual"])
        writes = list(self.api.writes)
        plan = self.workflow.plan_board("Board", ["Title", "Status", "Priority"])
        self.assertFalse(self.workflow.apply_board(plan, approved=True)["verified"])
        self.assertEqual(writes, self.api.writes)

    def test_wrong_filter_and_visible_order_are_detected(self):
        self.configure()
        plan = self.workflow.plan_board("Board", ["Title", "Status", "Priority"])
        self.api.views[0]["filter"] = "repo:somewhere/else"
        self.api.views[0]["configuration"]["visibleFields"]["nodes"].reverse()
        result = self.workflow.verify_board(plan)
        self.assertFalse(result["checks"]["filter"])
        self.assertFalse(result["checks"]["fields"])

    def test_project_connections_are_paginated(self):
        self.api.page_size = 1
        self.configure()
        self.assertGreater(len(self.workflow.fields()), 1)

    def test_wrong_field_type_does_not_create_duplicate(self):
        self.api.fields.append(self.api.field("Priority", "ProjectV2Field"))
        with self.assertRaises(GitHubFailure) as failure:
            self.workflow.plan_field("Priority", ["P0"])
        self.assertEqual(failure.exception.category, "field_type_conflict")
        self.assertFalse(self.api.writes)

    def test_wrong_repository_issue_association_is_rejected(self):
        self.configure()
        self.workflow.associate(1, {}, approved=True)
        self.api.items[0]["content"]["repository"]["id"] = "R_other"
        with self.assertRaises(GitHubFailure) as failure:
            self.workflow.associate(1, {}, approved=True)
        self.assertEqual(failure.exception.category, "verification")


if __name__ == "__main__":
    unittest.main()
