import sys
sys.path.insert(0, "scripts")

import unittest
from skill_trigger import SkillTriggerEngine, TriggerRule


class TestTriggerRule(unittest.TestCase):
    def test_create_rule(self):
        rule = TriggerRule(
            rule_id="TR-001",
            event="task_start",
            task_type_pattern="api_*",
            skill_card_path="skill-cards/patterns/api-integration.md",
            priority=0.8,
        )
        self.assertEqual(rule.rule_id, "TR-001")
        self.assertEqual(rule.event, "task_start")

    def test_rule_matches_wildcard(self):
        rule = TriggerRule("TR-001", "task_start", "api_*", "path.md", 0.8)
        self.assertTrue(rule.matches("api_integration"))
        self.assertTrue(rule.matches("api_testing"))
        self.assertFalse(rule.matches("data_validation"))

    def test_rule_matches_exact(self):
        rule = TriggerRule("TR-001", "task_start", "doc_converter", "path.md", 0.8)
        self.assertTrue(rule.matches("doc_converter"))
        self.assertFalse(rule.matches("api_integration"))


class TestSkillTriggerEngine(unittest.TestCase):
    def _make_engine(self):
        engine = SkillTriggerEngine()
        engine.add_rule(TriggerRule("TR-001", "task_start", "api_*",
                                    "skill-cards/patterns/api.md", 0.8))
        engine.add_rule(TriggerRule("TR-002", "task_start", "api_*",
                                    "skill-cards/patterns/retry.md", 0.6))
        engine.add_rule(TriggerRule("TR-003", "task_start", "data_*",
                                    "skill-cards/patterns/validation.md", 0.7))
        engine.add_rule(TriggerRule("TR-004", "task_complete", "*",
                                    "skill-cards/workflows/writeback.md", 0.5))
        return engine

    def test_find_matching_rules(self):
        engine = self._make_engine()
        matches = engine.find_matching("task_start", "api_integration")
        self.assertEqual(len(matches), 2)
        # Sorted by priority descending
        self.assertEqual(matches[0].rule_id, "TR-001")

    def test_no_matching_rules(self):
        engine = self._make_engine()
        matches = engine.find_matching("task_start", "unknown_type")
        self.assertEqual(len(matches), 0)

    def test_wildcard_matches_all(self):
        engine = self._make_engine()
        matches = engine.find_matching("task_complete", "anything")
        self.assertEqual(len(matches), 1)

    def test_get_recommended_skills(self):
        engine = self._make_engine()
        skills = engine.get_recommended_skills("task_start", "api_integration")
        self.assertEqual(len(skills), 2)
        self.assertEqual(skills[0]["priority"], 0.8)

    def test_load_rules_from_json(self):
        import tempfile, json, os
        rules = [
            {"rule_id": "TR-010", "event": "task_start", "task_type_pattern": "test_*",
             "skill_card_path": "test.md", "priority": 0.9}
        ]
        with tempfile.NamedTemporaryFile(mode="w", suffix=".json", delete=False) as f:
            json.dump(rules, f)
            path = f.name
        try:
            engine = SkillTriggerEngine()
            engine.load_rules(path)
            matches = engine.find_matching("task_start", "test_something")
            self.assertEqual(len(matches), 1)
        finally:
            os.unlink(path)
