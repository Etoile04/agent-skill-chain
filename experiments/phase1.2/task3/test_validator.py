"""
Tests for the skill card batch validation engine.
Run with: python -m unittest test_validator -v
"""

import os
import json
import tempfile
import unittest
from pathlib import Path

from validator import (
    SkillCardParser,
    CardValidator,
    BatchValidator,
    ValidationResult,
    Issue,
    Severity,
    BatchResult,
    SKILL_CARD_SCHEMA,
)


# ---------------------------------------------------------------------------
# Test data helpers
# ---------------------------------------------------------------------------

VALID_CARD_FRONTMATTER = """---
id: sc-20260502-test
type: pattern
category: patterns
task_types:
  - 测试任务
avg_reward: 0.75
usage_count: 5
created: 2026-05-02
updated: 2026-05-02
status: active
sources:
  - memory/2026-05-02.md
transfer_mode: indirect
---

# 测试卡片

## ✅ 成功经验 (e_success)

### 有效的策略
- 测试策略

## ❌ 失败教训 (e_mistake)

### 踩过的坑
- 测试失败

## 🔄 推荐工作流 (e_workflow)

### 标准流程
1. 测试步骤
"""

MISSING_REQUIRED_FIELDS = """---
id: sc-20260502-incomplete
type: pattern
category: patterns
task_types:
  - 不完整卡片
---

# 不完整卡片

## ✅ 成功经验 (e_success)
"""

BAD_TYPES_CARD = """---
id: sc-20260502-badtype
type: invalid_type
category: patterns
task_types: not_a_list
avg_reward: "not_a_number"
usage_count: -1
created: bad-date
updated: 2026-05-02
status: active
sources:
  - test.md
---

# 坏类型卡片

## ✅ 成功经验 (e_success)
"""

NO_FRONTMATTER = """This is a plain markdown file with no frontmatter at all.

# Just a heading

Some content.
"""

EMPTY_FRONTMATTER = """---
---

# Empty frontmatter
"""


class TestSkillCardParser(unittest.TestCase):

    def test_parse_valid_card(self):
        with tempfile.NamedTemporaryFile(mode="w", suffix=".md", delete=False, encoding="utf-8") as f:
            f.write(VALID_CARD_FRONTMATTER)
            f.flush()
            card = SkillCardParser.parse(f.name)
        os.unlink(f.name)

        self.assertIsInstance(card, dict)
        self.assertIn("metadata", card)
        self.assertIn("body", card)
        self.assertEqual(card["metadata"]["id"], "sc-20260502-test")
        self.assertEqual(card["metadata"]["type"], "pattern")
        self.assertIn("成功经验", card["body"])

    def test_parse_no_frontmatter(self):
        with tempfile.NamedTemporaryFile(mode="w", suffix=".md", delete=False, encoding="utf-8") as f:
            f.write(NO_FRONTMATTER)
            f.flush()
            with self.assertRaises(ValueError) as ctx:
                SkillCardParser.parse(f.name)
        os.unlink(f.name)
        self.assertIn("frontmatter", str(ctx.exception).lower())

    def test_parse_empty_frontmatter(self):
        with tempfile.NamedTemporaryFile(mode="w", suffix=".md", delete=False, encoding="utf-8") as f:
            f.write(EMPTY_FRONTMATTER)
            f.flush()
            # Empty frontmatter parses as None — should raise
            with self.assertRaises(ValueError):
                SkillCardParser.parse(f.name)
        os.unlink(f.name)

    def test_parse_nonexistent_file(self):
        with self.assertRaises(FileNotFoundError):
            SkillCardParser.parse("/tmp/nonexistent_card_12345.md")


class TestCardValidator(unittest.TestCase):

    def setUp(self):
        self.validator = CardValidator()

    def _parse_and_validate(self, content):
        with tempfile.NamedTemporaryFile(mode="w", suffix=".md", delete=False, encoding="utf-8") as f:
            f.write(content)
            f.flush()
            card = SkillCardParser.parse(f.name)
        os.unlink(f.name)
        return self.validator.validate(card)

    def test_valid_card_passes(self):
        result = self._parse_and_validate(VALID_CARD_FRONTMATTER)
        self.assertEqual(result.status, "pass")
        errors = [i for i in result.issues if i["severity"] == "error"]
        self.assertEqual(len(errors), 0, f"Unexpected errors: {errors}")

    def test_missing_required_fields(self):
        result = self._parse_and_validate(MISSING_REQUIRED_FIELDS)
        self.assertEqual(result.status, "error")
        error_fields = {i["field"] for i in result.issues if i["severity"] == "error"}
        # Should flag: avg_reward, usage_count, created, updated, status, sources
        expected_missing = {"avg_reward", "usage_count", "created", "updated", "status", "sources"}
        self.assertTrue(expected_missing.issubset(error_fields),
                        f"Expected {expected_missing} in error fields, got {error_fields}")

    def test_bad_types_and_enum(self):
        result = self._parse_and_validate(BAD_TYPES_CARD)
        self.assertEqual(result.status, "error")
        error_fields = {i["field"] for i in result.issues if i["severity"] == "error"}
        # type: invalid enum, task_types: wrong type, avg_reward: wrong type,
        # usage_count: negative, created: pattern mismatch
        self.assertIn("type", error_fields)
        self.assertIn("task_types", error_fields)
        self.assertIn("avg_reward", error_fields)

    def test_reward_range(self):
        # Test reward > 1.0
        card_over = VALID_CARD_FRONTMATTER.replace("avg_reward: 0.75", "avg_reward: 1.5")
        result = self._parse_and_validate(card_over)
        errors = [i for i in result.issues if i["severity"] == "error" and i["field"] == "avg_reward"]
        self.assertTrue(len(errors) > 0, "Expected avg_reward above max error")

        # Test reward < 0
        card_under = VALID_CARD_FRONTMATTER.replace("avg_reward: 0.75", "avg_reward: -0.5")
        result = self._parse_and_validate(card_under)
        errors = [i for i in result.issues if i["severity"] == "error" and i["field"] == "avg_reward"]
        self.assertTrue(len(errors) > 0, "Expected avg_reward below min error")

    def test_invalid_status_enum(self):
        card = VALID_CARD_FRONTMATTER.replace("status: active", "status: unknown")
        result = self._parse_and_validate(card)
        errors = [i for i in result.issues if i["severity"] == "error" and "status" in i["field"]]
        self.assertTrue(len(errors) > 0)

    def test_id_pattern(self):
        card = VALID_CARD_FRONTMATTER.replace("id: sc-20260502-test", "id: invalid-id-format")
        result = self._parse_and_validate(card)
        errors = [i for i in result.issues if i["severity"] == "error" and i["field"] == "id"]
        self.assertTrue(len(errors) > 0)

    def test_body_missing_sections_info_only(self):
        # A card with valid frontmatter but minimal body
        minimal = """---
id: sc-20260502-minimal
type: domain
category: domains
task_types:
  - minimal test
avg_reward: 0.5
usage_count: 0
created: 2026-05-02
updated: 2026-05-02
status: active
sources:
  - test.md
---

# Minimal Card

Just some content without standard sections.
"""
        result = self._parse_and_validate(minimal)
        # Should be warn or pass, not error — missing sections are INFO
        info_issues = [i for i in result.issues if i["severity"] == "info"]
        self.assertTrue(len(info_issues) > 0, "Expected info issues for missing body sections")
        self.assertNotEqual(result.status, "error")


class TestBatchValidator(unittest.TestCase):

    def _create_card_dir(self, cards: dict):
        """Create a temp dir with named card files. cards = {filename: content}"""
        tmpdir = tempfile.mkdtemp()
        for name, content in cards.items():
            filepath = os.path.join(tmpdir, name)
            os.makedirs(os.path.dirname(filepath), exist_ok=True)
            with open(filepath, "w", encoding="utf-8") as f:
                f.write(content)
        return tmpdir

    def test_scan_with_mixed_cards(self):
        tmpdir = self._create_card_dir({
            "good.md": VALID_CARD_FRONTMATTER,
            "bad.md": MISSING_REQUIRED_FIELDS,
            "nofm.md": NO_FRONTMATTER,
        })
        try:
            bv = BatchValidator()
            result = bv.scan_directory(tmpdir)
            self.assertEqual(result.total, 3)
            self.assertGreater(result.errored, 0)
        finally:
            import shutil
            shutil.rmtree(tmpdir)

    def test_scan_nonexistent_directory(self):
        bv = BatchValidator()
        result = bv.scan_directory("/tmp/nonexistent_dir_99999")
        self.assertEqual(result.total, 1)
        self.assertEqual(result.errored, 1)

    def test_duplicate_id_detection(self):
        card1 = VALID_CARD_FRONTMATTER
        card2 = VALID_CARD_FRONTMATTER.replace("transfer_mode: indirect", "transfer_mode: direct")
        tmpdir = self._create_card_dir({
            "card1.md": card1,
            "sub/card2.md": card2,
        })
        try:
            bv = BatchValidator()
            result = bv.scan_directory(tmpdir)
            # Should detect duplicate id sc-20260502-test
            all_issues = []
            for r in result.results:
                all_issues.extend(r.get("issues", []))
            dup_issues = [i for i in all_issues if "Duplicate" in i.get("message", "")]
            self.assertTrue(len(dup_issues) > 0, "Expected duplicate id warning")
        finally:
            import shutil
            shutil.rmtree(tmpdir)

    def test_single_file_exception_does_not_stop_batch(self):
        """If one file raises an unexpected exception, others still get validated."""
        tmpdir = tempfile.mkdtemp()
        # Write a valid card
        with open(os.path.join(tmpdir, "valid.md"), "w", encoding="utf-8") as f:
            f.write(VALID_CARD_FRONTMATTER)
        # Write a broken card (empty file)
        with open(os.path.join(tmpdir, "empty.md"), "w", encoding="utf-8") as f:
            f.write("")
        # Write another valid card with different id
        card2 = VALID_CARD_FRONTMATTER.replace("sc-20260502-test", "sc-20260502-test2")
        with open(os.path.join(tmpdir, "valid2.md"), "w", encoding="utf-8") as f:
            f.write(card2)

        try:
            bv = BatchValidator()
            result = bv.scan_directory(tmpdir)
            self.assertEqual(result.total, 3)
            self.assertGreater(result.errored, 0)  # empty file
            self.assertGreater(result.passed, 0)   # valid cards
        finally:
            import shutil
            shutil.rmtree(tmpdir)


class TestRealSkillCards(unittest.TestCase):
    """Integration test against the actual skill-cards directory."""

    CARDS_DIR = "/tmp/agent-skill-chain/skill-cards/"

    def test_real_cards_scan(self):
        if not os.path.exists(self.CARDS_DIR):
            self.skipTest(f"Real cards directory not found: {self.CARDS_DIR}")

        bv = BatchValidator()
        result = bv.scan_directory(self.CARDS_DIR)

        print(f"\n=== Real Cards Scan Results ===")
        print(f"Total: {result.total}, Passed: {result.passed}, Warned: {result.warned}, Errored: {result.errored}")
        for r in result.results:
            status_icon = {"pass": "✅", "warn": "⚠️", "error": "❌"}.get(r["status"], "?")
            rel = os.path.relpath(r["path"], self.CARDS_DIR)
            print(f"  {status_icon} {rel}: {r['status']}")
            for issue in r.get("issues", []):
                print(f"      [{issue['severity']}] {issue['field']}: {issue['message']}")
            if r.get("error"):
                print(f"      PARSE ERROR: {r['error']}")

        # All files should be scannable (no crashes)
        self.assertEqual(result.total, 12, f"Expected 12 card files, got {result.total}")

        # Serialize to JSON (for step result)
        json_output = json.dumps(result.to_dict(), indent=2, ensure_ascii=False)
        self.assertIsInstance(json_output, str)
        parsed_back = json.loads(json_output)
        self.assertEqual(parsed_back["total"], 12)


if __name__ == "__main__":
    unittest.main()
