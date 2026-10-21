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

    def test_partial_board_create_resumes_filter_update(self):
        self.workflow.apply_field(self.workflow.plan_field("Priority", ["P0"]), approved=True)
        plan = self.workflow.plan_board("Board", ["Title", "Status", "Priority"])
        self.api.fail_after = "createProjectV2View"
        with self.assertRaises(GitHubFailure):
            self.workflow.apply_board(plan, approved=True)
        self.assertEqual(self.api.views[0]["filter"], "")
        self.assertTrue(self.workflow.apply_board(plan, approved=True)["verified"])
        self.assertEqual(len(self.api.views), 1)

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
