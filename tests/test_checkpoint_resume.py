import unittest, subprocess, os, json, tempfile

class TestCheckpointResume(unittest.TestCase):
    def test_checkpoint_creates_state_file(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            state_file = os.path.join(tmpdir, "state.json")
            subprocess.run([
                "bash", "scripts/checkpoint-resume.sh", "checkpoint",
                state_file, "T-001", "step-3", "resume from here"
            ], timeout=5, cwd="/tmp/agent-skill-chain/.worktrees/phase2")
            self.assertTrue(os.path.exists(state_file))
            data = json.load(open(state_file))
            self.assertEqual(data["task_id"], "T-001")
            self.assertEqual(data["completed_steps"][-1], "step-3")

    def test_resume_reads_state(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            state_file = os.path.join(tmpdir, "state.json")
            subprocess.run([
                "bash", "scripts/checkpoint-resume.sh", "checkpoint",
                state_file, "T-001", "step-2", "continue"
            ], timeout=5, cwd="/tmp/agent-skill-chain/.worktrees/phase2")
            result = subprocess.run([
                "bash", "scripts/checkpoint-resume.sh", "resume",
                state_file, "T-001"
            ], capture_output=True, text=True, timeout=5,
               cwd="/tmp/agent-skill-chain/.worktrees/phase2")
            self.assertIn("continue", result.stdout)

    def test_multiple_checkpoints(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            state_file = os.path.join(tmpdir, "state.json")
            subprocess.run(["bash", "scripts/checkpoint-resume.sh", "checkpoint",
                          state_file, "T-001", "step-1", "hint1"],
                          timeout=5, cwd="/tmp/agent-skill-chain/.worktrees/phase2")
            subprocess.run(["bash", "scripts/checkpoint-resume.sh", "checkpoint",
                          state_file, "T-001", "step-2", "hint2"],
                          timeout=5, cwd="/tmp/agent-skill-chain/.worktrees/phase2")
            data = json.load(open(state_file))
            self.assertEqual(len(data["completed_steps"]), 2)
