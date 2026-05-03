import unittest, subprocess, os, tempfile, time, json

LOCK_CWD = "/tmp/agent-skill-chain/.worktrees/phase2"

class TestLock(unittest.TestCase):
    def test_acquire_and_release(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            lockfile = os.path.join(tmpdir, "test.lock")
            result = subprocess.run(
                ["bash", "scripts/lock.sh", "acquire", lockfile, "30"],
                capture_output=True, text=True, timeout=5,
                cwd=LOCK_CWD
            )
            self.assertEqual(result.returncode, 0)
            self.assertTrue(os.path.exists(lockfile))
            # Release
            result = subprocess.run(
                ["bash", "scripts/lock.sh", "release", lockfile],
                capture_output=True, text=True, timeout=5,
                cwd=LOCK_CWD
            )
            self.assertEqual(result.returncode, 0)
            self.assertFalse(os.path.exists(lockfile))

    def test_double_acquire_fails(self):
        """Second acquire should fail while lock is fresh and not yet expired."""
        with tempfile.TemporaryDirectory() as tmpdir:
            lockfile = os.path.join(tmpdir, "test.lock")
            # First acquire succeeds
            result1 = subprocess.run(
                ["bash", "scripts/lock.sh", "acquire", lockfile, "30"],
                capture_output=True, text=True, timeout=5,
                cwd=LOCK_CWD
            )
            self.assertEqual(result1.returncode, 0, f"First acquire should succeed: {result1.stderr}")
            self.assertTrue(os.path.exists(lockfile))
            # Second acquire should fail (lock is fresh, TTL=30s)
            result2 = subprocess.run(
                ["bash", "scripts/lock.sh", "acquire", lockfile, "30"],
                capture_output=True, text=True, timeout=5,
                cwd=LOCK_CWD
            )
            self.assertNotEqual(result2.returncode, 0,
                f"Second acquire should fail while lock is held. stdout={result2.stdout} stderr={result2.stderr}")

    def test_lock_contains_metadata(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            lockfile = os.path.join(tmpdir, "test.lock")
            subprocess.run(
                ["bash", "scripts/lock.sh", "acquire", lockfile, "30"],
                timeout=5, cwd=LOCK_CWD
            )
            with open(lockfile) as f:
                data = json.load(f)
            self.assertIn("PID", data)
            self.assertIn("acquired_at", data)
            self.assertIn("ttl_seconds", data)
            self.assertIn("acquired_at_epoch", data)

    def test_stale_lock_auto_cleanup(self):
        """A lock older than its TTL should be auto-cleaned on next acquire."""
        with tempfile.TemporaryDirectory() as tmpdir:
            lockfile = os.path.join(tmpdir, "test.lock")
            # Create a stale lock with epoch timestamp in the past
            now = int(time.time())
            stale_epoch = now - 100  # 100 seconds ago
            with open(lockfile, "w") as f:
                json.dump({
                    "PID": 99999999,
                    "acquired_at": "2020-01-01T00:00:00+08:00",
                    "acquired_at_epoch": stale_epoch,
                    "ttl_seconds": 30
                }, f)
            # Acquire should succeed (stale lock cleaned up)
            result = subprocess.run(
                ["bash", "scripts/lock.sh", "acquire", lockfile, "30"],
                capture_output=True, text=True, timeout=5,
                cwd=LOCK_CWD
            )
            self.assertEqual(result.returncode, 0, f"Should succeed with stale lock: {result.stderr}")
