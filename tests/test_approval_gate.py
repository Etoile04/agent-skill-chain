import unittest
import tempfile
import os
import sys
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'scripts'))

from approval_gate import ApprovalGate, ApprovalRequest, ApprovalStatus


class TestApprovalRequest(unittest.TestCase):
    def test_create_request(self):
        req = ApprovalRequest(
            request_id="req-001",
            operation="delete_database",
            agent_id="coding-a2a",
            risk_level="high",
            details={"target": "production_db"}
        )
        self.assertEqual(req.request_id, "req-001")
        self.assertEqual(req.status, ApprovalStatus.PENDING)

    def test_request_requires_approval_for_high_risk(self):
        req = ApprovalRequest("req-002", "modify_config", "agent-1", "high", {})
        self.assertTrue(req.requires_human_approval)


class TestApprovalGate(unittest.TestCase):
    def setUp(self):
        self.tmpdir = tempfile.mkdtemp()
        self.gate = ApprovalGate(
            persistence_path=os.path.join(self.tmpdir, "approvals.json"),
            auto_approve_low_risk=True
        )

    def tearDown(self):
        import shutil
        shutil.rmtree(self.tmpdir, ignore_errors=True)

    def test_submit_request(self):
        req_id = self.gate.submit(
            operation="run_tests",
            agent_id="coding-a2a",
            risk_level="low",
            details={}
        )
        self.assertIsNotNone(req_id)
        req = self.gate.get_request(req_id)
        self.assertEqual(req.operation, "run_tests")

    def test_auto_approve_low_risk(self):
        req_id = self.gate.submit("run_tests", "coding-a2a", "low", {})
        req = self.gate.get_request(req_id)
        self.assertEqual(req.status, ApprovalStatus.APPROVED)

    def test_high_risk_needs_manual_approval(self):
        req_id = self.gate.submit("delete_files", "coding-a2a", "high", {"path": "/important"})
        req = self.gate.get_request(req_id)
        self.assertEqual(req.status, ApprovalStatus.PENDING)

    def test_approve_manually(self):
        req_id = self.gate.submit("delete_files", "coding-a2a", "high", {})
        result = self.gate.approve(req_id, approver="human")
        self.assertTrue(result)
        req = self.gate.get_request(req_id)
        self.assertEqual(req.status, ApprovalStatus.APPROVED)

    def test_reject_manually(self):
        req_id = self.gate.submit("delete_files", "coding-a2a", "high", {})
        result = self.gate.reject(req_id, approver="human", reason="too risky")
        self.assertTrue(result)
        req = self.gate.get_request(req_id)
        self.assertEqual(req.status, ApprovalStatus.REJECTED)

    def test_cannot_approve_twice(self):
        req_id = self.gate.submit("delete_files", "coding-a2a", "high", {})
        self.gate.approve(req_id, approver="human")
        result = self.gate.approve(req_id, approver="human2")
        self.assertFalse(result)

    def test_persistence(self):
        path = os.path.join(self.tmpdir, "approvals.json")
        gate1 = ApprovalGate(path, auto_approve_low_risk=True)
        gate1.submit("op1", "a1", "high", {})
        gate1.save()
        gate2 = ApprovalGate(path, auto_approve_low_risk=True)
        pending = gate2.get_pending()
        self.assertEqual(len(pending), 1)

    def test_get_pending_requests(self):
        self.gate.submit("op1", "a1", "high", {})
        self.gate.submit("op2", "a1", "high", {})
        self.gate.submit("op3", "a1", "low", {})
        pending = self.gate.get_pending()
        self.assertEqual(len(pending), 2)


if __name__ == "__main__":
    unittest.main()
