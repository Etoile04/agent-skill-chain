import unittest
import tempfile
import os
import sys
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'scripts'))

from governance_versioner import GovernanceVersioner, ConfigVersion


class TestConfigVersion(unittest.TestCase):
    def test_create_version(self):
        v = ConfigVersion(
            version="1.0.0",
            config={"approval_rules": {"high_risk": "manual"}},
            author="admin",
            description="Initial governance config"
        )
        self.assertEqual(v.version, "1.0.0")
        self.assertEqual(v.author, "admin")

    def test_version_has_timestamp(self):
        v = ConfigVersion("1.0.0", {}, "admin", "test")
        self.assertIsNotNone(v.timestamp)


class TestGovernanceVersioner(unittest.TestCase):
    def setUp(self):
        self.tmpdir = tempfile.mkdtemp()
        self.versioner = GovernanceVersioner(os.path.join(self.tmpdir, "governance.json"))

    def tearDown(self):
        import shutil
        shutil.rmtree(self.tmpdir, ignore_errors=True)

    def test_create_initial_config(self):
        config = {"approval_rules": {"high_risk": "manual"}, "agents": {}}
        self.versioner.commit(config, author="admin", description="Initial config")
        current = self.versioner.get_current()
        self.assertEqual(current.config["approval_rules"]["high_risk"], "manual")

    def test_version_increments(self):
        self.versioner.commit({"v": 1}, "admin", "v1")
        self.versioner.commit({"v": 2}, "admin", "v2")
        history = self.versioner.get_history()
        self.assertEqual(len(history), 2)
        self.assertEqual(history[1]["version"], "0.2.0")

    def test_rollback(self):
        self.versioner.commit({"v": 1}, "admin", "v1")
        self.versioner.commit({"v": 2}, "admin", "v2")
        self.versioner.rollback(1)
        current = self.versioner.get_current()
        self.assertEqual(current.config["v"], 1)

    def test_cannot_rollback_too_far(self):
        self.versioner.commit({"v": 1}, "admin", "v1")
        result = self.versioner.rollback(5)
        self.assertFalse(result)

    def test_diff_between_versions(self):
        self.versioner.commit({"a": 1, "b": 2}, "admin", "v1")
        self.versioner.commit({"a": 1, "b": 3, "c": 4}, "admin", "v2")
        diff = self.versioner.diff(0, 1)
        self.assertIn("added", diff)
        self.assertIn("changed", diff)

    def test_persistence(self):
        path = os.path.join(self.tmpdir, "governance.json")
        gv1 = GovernanceVersioner(path)
        gv1.commit({"x": 1}, "admin", "test")
        gv1.save()
        gv2 = GovernanceVersioner(path)
        current = gv2.get_current()
        self.assertIsNotNone(current)
        self.assertEqual(current.config["x"], 1)

    def test_get_version_at(self):
        self.versioner.commit({"v": 1}, "admin", "v1")
        self.versioner.commit({"v": 2}, "admin", "v2")
        self.versioner.commit({"v": 3}, "admin", "v3")
        v1 = self.versioner.get_version_at(0)
        self.assertEqual(v1.config["v"], 1)


if __name__ == "__main__":
    unittest.main()
