import unittest
import tempfile
import os
import sys
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'scripts'))

from principle_store import Principle, PrincipleStore
from bias_detector import BiasPattern, BiasDetector
from reflection_loop import ReflectionLoop
from autonomous_improver import AutonomousImprover, ImprovementProposal


class TestImprovementProposal(unittest.TestCase):
    def test_create_proposal(self):
        proposal = ImprovementProposal(
            proposal_id="IMP-001",
            area="testing",
            current_state="No integration tests",
            proposed_improvement="Add integration test for all module pairs",
            rationale="3 integration failures in past week",
            priority="high"
        )
        self.assertEqual(proposal.proposal_id, "IMP-001")
        self.assertEqual(proposal.priority, "high")


class TestAutonomousImprover(unittest.TestCase):
    def setUp(self):
        self.tmpdir = tempfile.mkdtemp()
        self.principle_store = PrincipleStore(os.path.join(self.tmpdir, "p.json"))
        self.bias_detector = BiasDetector(os.path.join(self.tmpdir, "b.json"))
        self.reflection = ReflectionLoop(self.principle_store, self.bias_detector)
        self.improver = AutonomousImprover(
            self.principle_store, self.bias_detector, self.reflection
        )

    def tearDown(self):
        import shutil
        shutil.rmtree(self.tmpdir, ignore_errors=True)

    def test_analyze_error_patterns(self):
        for _ in range(3):
            self.reflection.reflect_on_error({
                "error_type": "test_failure",
                "symptom": "test not run before commit",
                "root_cause": "skipped verification",
                "fix_applied": "run tests"
            })
        patterns = self.improver.analyze_error_patterns()
        self.assertGreater(len(patterns), 0)

    def test_propose_improvement(self):
        for i in range(3):
            p = Principle(f"P-{i}", f"Principle {i}", "desc", "error", "trigger", "action", ["test_failure"])
            p.record_application(prevented_error=False)
            self.principle_store.add(p)
        proposals = self.improver.propose_improvements()
        self.assertGreater(len(proposals), 0)
        for prop in proposals:
            self.assertTrue(len(prop.proposed_improvement) > 0)
            self.assertIn(prop.priority, ["low", "medium", "high"])

    def test_identify_weak_principles(self):
        p1 = Principle("P-good", "Good", "d", "r", "t", "a", [])
        p1.record_application(True)
        p1.record_application(True)
        p1.record_application(True)
        p2 = Principle("P-weak", "Weak", "d", "r", "t", "a", [])
        p2.record_application(False)
        p2.record_application(False)
        p2.record_application(False)
        self.principle_store.add(p1)
        self.principle_store.add(p2)
        weak = self.improver.identify_weak_principles(threshold=0.3)
        self.assertEqual(len(weak), 1)
        self.assertEqual(weak[0].principle_id, "P-weak")

    def test_suggest_principle_refinements(self):
        p = Principle("P-1", "Original", "desc", "error", "test fails", "run tests", [])
        p.record_application(False)
        p.record_application(False)
        self.principle_store.add(p)
        refinements = self.improver.suggest_refinements(p)
        self.assertGreater(len(refinements), 0)
        self.assertIn("suggestion", refinements[0])

    def test_full_improvement_cycle(self):
        for _ in range(5):
            self.reflection.reflect_on_error({
                "error_type": "scope_creep",
                "symptom": "added unrequested features",
                "root_cause": "no scope verification step",
                "fix_applied": "check spec before implementing"
            })
        proposals = self.improver.run_improvement_cycle()
        self.assertIsInstance(proposals, list)


if __name__ == "__main__":
    unittest.main()
