"""
Tests for the skill card auto-fix engine.
Run with: python -m unittest test_autofix -v
"""

import os
import json
import copy
import shutil
import tempfile
import unittest
from pathlib import Path

from validator import CardValidator, SkillCardParser, SKILL_CARD_SCHEMA
from autofix import AutoFixer, FixPlan, FixedCard, FixResult, FixAction, FILL_DEFAULTS


# ---------------------------------------------------------------------------
# Test data
# ---------------------------------------------------------------------------

VALID_CARD_MD = """---
id: sc-20260503-valid
type: pattern
category: patterns
task_types:
  - valid test
avg_reward: 0.8
usage_count: 10
created: 2026-05-03
updated: 2026-05-03
status: active
sources:
  - test.md
priority: medium
version: 0.1.0
tags:
  - test
---

# Valid Card

## ✅ 成功经验 (e_success)
- Good stuff

## ❌ 失败教训 (e_mistake)
- Bad stuff

## 🔄 推荐工作流 (e_workflow)
1. Step one
"""

# Missing optional fields that have defaults
MISSING_DEFAULTS_MD = """---
id: sc-20260503-nodefaults
type: pattern
category: patterns
task_types:
  - test
avg_reward: 0.5
usage_count: 1
created: 2026-05-03
updated: 2026-05-03
status: active
sources:
  - test.md
---

# No Defaults Card

## ✅ 成功经验 (e_success)
- Testing
"""

# Bad date format
BAD_DATE_MD = """---
id: sc-20260503-baddate
type: pattern
category: patterns
task_types:
  - test
avg_reward: 0.6
usage_count: 2
created: 2026.05.03
updated: 2026/05/03
status: active
sources:
  - test.md
priority: high
version: 1.0.0
tags:
  - date-test
---

# Bad Date Card

## ✅ 成功经验 (e_success)
- Date testing
"""

# Description with whitespace + array with empty strings
WHITESPACY_MD = """---
id: sc-20260503-whitespace
type: pattern
category: patterns
task_types:
  - whitespace test
avg_reward: 0.4
usage_count: 0
created: 2026-05-03
updated: 2026-05-03
status: active
sources:
  - test.md
description: "  this has leading and trailing spaces  "
tags:
  - valid-tag
  - ""
  - another-tag
  - ""
---

# Whitespace Card

## ✅ 成功经验 (e_success)
- Whitespace testing
"""

# Missing required field that has NO default (manual fix required)
MISSING_REQUIRED_NO_DEFAULT_MD = """---
id: sc-20260503-manual
type: pattern
category: patterns
task_types:
  - manual test
status: active
---

# Manual Fix Required

## ✅ 成功经验 (e_success)
- Manual
"""

# Kitchen sink: multiple fixable issues at once
KITCHEN_SINK_MD = """---
id: sc-20260503-kitchen
type: pattern
category: patterns
task_types:
  - ""
  - kitchen sink test
avg_reward: 0.7
usage_count: 3
created: 20260503
updated: 2026.05.03
status: active
sources:
  - test.md
  - ""
description: "  needs trimming  "
---

# Kitchen Sink

## ✅ 成功经验 (e_success)
- Everything is broken but fixable
"""


class TestFixPlan(unittest.TestCase):
    """Test FixPlan data structure."""

    def test_empty_plan(self):
        plan = FixPlan()
        d = plan.to_dict()
        self.assertEqual(d["fixable"], [])
        self.assertEqual(d["manual_fix_required"], [])

    def test_plan_with_items(self):
        plan = FixPlan(
            fixable=[{"field": "priority", "message": "missing", "fixable": True}],
            manual_fix_required=[{"field": "id", "message": "bad pattern", "fixable": False}],
        )
        d = plan.to_dict()
        self.assertEqual(len(d["fixable"]), 1)
        self.assertEqual(len(d["manual_fix_required"]), 1)


class TestAnalyze(unittest.TestCase):
    """Test AutoFixer.analyze()."""

    def setUp(self):
        self.fixer = AutoFixer()

    def _analyze_md(self, md_content):
        with tempfile.NamedTemporaryFile(mode="w", suffix=".md", delete=False, encoding="utf-8") as f:
            f.write(md_content)
            f.flush()
            card = SkillCardParser.parse(f.name)
        os.unlink(f.name)
        return self.fixer.analyze(card)

    def test_valid_card_no_fixable(self):
        plan = self._analyze_md(VALID_CARD_MD)
        # Valid card may have info issues for missing body sections, but no fixable ones
        fixable_fields = {i["field"] for i in plan.fixable}
        # Should not need to fill defaults — card already has them
        self.assertNotIn("priority", fixable_fields)
        self.assertNotIn("version", fixable_fields)
        self.assertNotIn("tags", fixable_fields)

    def test_missing_defaults_are_fixable(self):
        plan = self._analyze_md(MISSING_DEFAULTS_MD)
        fixable_fields = {i["field"] for i in plan.fixable}
        self.assertIn("priority", fixable_fields)
        self.assertIn("version", fixable_fields)
        self.assertIn("tags", fixable_fields)

    def test_missing_required_no_default_is_manual(self):
        plan = self._analyze_md(MISSING_REQUIRED_NO_DEFAULT_MD)
        manual_fields = {i["field"] for i in plan.manual_fix_required}
        # avg_reward, usage_count, created, updated, sources are missing and have no defaults
        self.assertIn("avg_reward", manual_fields)
        self.assertIn("usage_count", manual_fields)
        self.assertIn("sources", manual_fields)

    def test_bad_date_is_fixable(self):
        plan = self._analyze_md(BAD_DATE_MD)
        fixable_fields = {i["field"] for i in plan.fixable}
        self.assertIn("created", fixable_fields)
        self.assertIn("updated", fixable_fields)

    def test_whitespace_description_fixable(self):
        plan = self._analyze_md(WHITESPACY_MD)
        fixable_fields = {i["field"] for i in plan.fixable}
        self.assertIn("description", fixable_fields)


class TestFix(unittest.TestCase):
    """Test AutoFixer.fix() — in-memory fixing."""

    def setUp(self):
        self.fixer = AutoFixer()

    def _fix_md(self, md_content, dry_run=False):
        with tempfile.NamedTemporaryFile(mode="w", suffix=".md", delete=False, encoding="utf-8") as f:
            f.write(md_content)
            f.flush()
            card = SkillCardParser.parse(f.name)
        os.unlink(f.name)
        return self.fixer.fix(card, dry_run=dry_run)

    def test_fill_missing_defaults(self):
        fixed = self._fix_md(MISSING_DEFAULTS_MD)
        meta = fixed.card["metadata"]
        self.assertEqual(meta.get("priority"), "medium")
        self.assertEqual(meta.get("version"), "0.1.0")
        self.assertEqual(meta.get("tags"), [])
        # Check changes recorded
        changed_fields = {c["field"] for c in fixed.changes}
        self.assertIn("priority", changed_fields)
        self.assertIn("version", changed_fields)
        self.assertIn("tags", changed_fields)

    def test_normalize_dates(self):
        fixed = self._fix_md(BAD_DATE_MD)
        meta = fixed.card["metadata"]
        self.assertEqual(meta.get("created"), "2026-05-03")
        self.assertEqual(meta.get("updated"), "2026-05-03")

    def test_trim_description(self):
        fixed = self._fix_md(WHITESPACY_MD)
        meta = fixed.card["metadata"]
        self.assertEqual(meta.get("description"), "this has leading and trailing spaces")

    def test_filter_empty_strings_from_arrays(self):
        fixed = self._fix_md(WHITESPACY_MD)
        meta = fixed.card["metadata"]
        tags = meta.get("tags", [])
        self.assertEqual(tags, ["valid-tag", "another-tag"])
        self.assertNotIn("", tags)

    def test_dry_run_does_not_modify_original(self):
        with tempfile.NamedTemporaryFile(mode="w", suffix=".md", delete=False, encoding="utf-8") as f:
            f.write(MISSING_DEFAULTS_MD)
            f.flush()
            card = SkillCardParser.parse(f.name)
        os.unlink(f.name)

        original_meta = copy.deepcopy(card["metadata"])
        fixed = self.fixer.fix(card, dry_run=True)

        # Original card metadata should be unchanged
        self.assertEqual(card["metadata"], original_meta)
        # But the returned card preview should have fixes
        self.assertIn("priority", fixed.card.get("metadata", {}))

    def test_revalidation_after_fix(self):
        fixed = self._fix_md(MISSING_DEFAULTS_MD)
        self.assertIsNotNone(fixed.revalidation)
        # After fixing, revalidation should not have errors for the fields we fixed
        reval_errors = [i for i in fixed.revalidation.get("issues", [])
                        if i["severity"] == "error"]
        error_fields = {i["field"] for i in reval_errors}
        self.assertNotIn("priority", error_fields)
        self.assertNotIn("version", error_fields)
        self.assertNotIn("tags", error_fields)

    def test_kitchen_sink_all_fixes_applied(self):
        fixed = self._fix_md(KITCHEN_SINK_MD)
        meta = fixed.card["metadata"]

        # Dates normalized
        self.assertEqual(meta.get("created"), "2026-05-03")
        self.assertEqual(meta.get("updated"), "2026-05-03")
        # Description trimmed
        self.assertEqual(meta.get("description"), "needs trimming")
        # Empty strings filtered from task_types
        self.assertEqual(meta.get("task_types"), ["kitchen sink test"])
        # Defaults filled
        self.assertEqual(meta.get("priority"), "medium")
        self.assertEqual(meta.get("version"), "0.1.0")
        # Empty strings filtered from sources
        self.assertEqual(meta.get("sources"), ["test.md"])
        # tags default filled
        self.assertEqual(meta.get("tags"), [])

        # Multiple changes recorded
        self.assertGreater(len(fixed.changes), 3, f"Expected multiple changes, got {len(fixed.changes)}")

    def test_valid_card_unchanged(self):
        fixed = self._fix_md(VALID_CARD_MD)
        # A valid card should have no changes on fields it already has
        # (it may get defaults for truly optional fields like related_cards)
        changed_fields = {c["field"] for c in fixed.changes}
        # These fields are already present, should NOT be changed
        self.assertNotIn("priority", changed_fields)
        self.assertNotIn("version", changed_fields)
        self.assertNotIn("tags", changed_fields)
        self.assertNotIn("description", changed_fields)


class TestFixFile(unittest.TestCase):
    """Test AutoFixer.fix_file() — file-level operation."""

    def setUp(self):
        self.fixer = AutoFixer()
        self.tmpdir = tempfile.mkdtemp()

    def tearDown(self):
        shutil.rmtree(self.tmpdir, ignore_errors=True)

    def _write_card(self, content, name="card.md"):
        path = os.path.join(self.tmpdir, name)
        with open(path, "w", encoding="utf-8") as f:
            f.write(content)
        return path

    def test_fix_file_creates_backup(self):
        path = self._write_card(MISSING_DEFAULTS_MD)
        result = self.fixer.fix_file(path, backup=True)
        self.assertTrue(result.success)
        self.assertIsNotNone(result.backup_path)
        self.assertTrue(os.path.exists(result.backup_path))
        self.assertTrue(result.backup_path.endswith(".bak"))

    def test_fix_file_no_backup(self):
        path = self._write_card(MISSING_DEFAULTS_MD)
        result = self.fixer.fix_file(path, backup=False)
        self.assertTrue(result.success)
        self.assertIsNone(result.backup_path)
        # No .bak file should exist
        self.assertFalse(os.path.exists(path + ".bak"))

    def test_dry_run_does_not_modify_file(self):
        path = self._write_card(MISSING_DEFAULTS_MD)
        with open(path, "r") as f:
            original_content = f.read()

        result = self.fixer.fix_file(path, dry_run=True)
        self.assertTrue(result.success)
        self.assertTrue(result.dry_run)

        with open(path, "r") as f:
            after_content = f.read()
        self.assertEqual(original_content, after_content)

    def test_fix_file_writes_corrected_content(self):
        path = self._write_card(MISSING_DEFAULTS_MD)
        result = self.fixer.fix_file(path, dry_run=False, backup=True)
        self.assertTrue(result.success)

        # Re-parse the file and check defaults are present
        card = SkillCardParser.parse(path)
        self.assertEqual(card["metadata"].get("priority"), "medium")
        self.assertEqual(card["metadata"].get("version"), "0.1.0")
        self.assertEqual(card["metadata"].get("tags"), [])

    def test_fix_file_parse_error(self):
        path = os.path.join(self.tmpdir, "bad.md")
        with open(path, "w", encoding="utf-8") as f:
            f.write("No frontmatter here at all\n")
        result = self.fixer.fix_file(path)
        self.assertFalse(result.success)
        self.assertIn("Parse error", result.error)

    def test_backup_preserves_original(self):
        path = self._write_card(KITCHEN_SINK_MD)
        result = self.fixer.fix_file(path, backup=True)
        self.assertTrue(result.success)

        # Backup should have original content
        with open(result.backup_path, "r") as f:
            bak_content = f.read()
        self.assertIn("20260503", bak_content)  # original non-standard date
        self.assertIn("needs trimming", bak_content)  # original has whitespace

        # Fixed file should have normalized content
        with open(path, "r") as f:
            fixed_content = f.read()
        self.assertIn("2026-05-03", fixed_content)

    def test_fix_and_revalidate_file(self):
        """Fix a file and re-validate to ensure no new errors introduced."""
        path = self._write_card(MISSING_DEFAULTS_MD)
        result = self.fixer.fix_file(path, dry_run=False)
        self.assertTrue(result.success)

        # Re-validate the fixed file
        card = SkillCardParser.parse(path)
        validator = CardValidator()
        val_result = validator.validate(card)

        # The fields we fixed should not produce errors
        error_fields = {i["field"] for i in val_result.issues if i["severity"] == "error"}
        self.assertNotIn("priority", error_fields)
        self.assertNotIn("version", error_fields)
        self.assertNotIn("tags", error_fields)


class TestFixResultSerialization(unittest.TestCase):
    """Test that FixResult, FixedCard, FixAction serialize correctly."""

    def test_fix_action_round_trip(self):
        action = FixAction(
            field="priority",
            issue="Required field 'priority' is missing",
            action="set default 'medium'",
            old_value=None,
            new_value="medium",
        )
        d = action.to_dict()
        self.assertEqual(d["field"], "priority")
        self.assertEqual(d["new_value"], "medium")

        # JSON-serializable
        json_str = json.dumps(d)
        parsed = json.loads(json_str)
        self.assertEqual(parsed["field"], "priority")

    def test_fixed_card_round_trip(self):
        fc = FixedCard(
            card={"metadata": {"id": "test"}, "body": ""},
            changes=[FixAction("f", "m", "a", None, "v").to_dict()],
            revalidation={"status": "pass", "issues": [], "path": "", "error": None},
        )
        d = fc.to_dict()
        self.assertIn("card", d)
        self.assertIn("changes", d)
        self.assertIn("revalidation", d)
        json_str = json.dumps(d)
        self.assertIsInstance(json_str, str)

    def test_fix_result_round_trip(self):
        fr = FixResult(
            path="/tmp/test.md",
            success=True,
            dry_run=False,
            backup_path="/tmp/test.md.bak",
            fixed_card=FixedCard().to_dict(),
        )
        d = fr.to_dict()
        self.assertEqual(d["path"], "/tmp/test.md")
        self.assertTrue(d["success"])
        json_str = json.dumps(d)
        self.assertIsInstance(json_str, str)


class TestEdgeCases(unittest.TestCase):
    """Edge cases and boundary conditions."""

    def setUp(self):
        self.fixer = AutoFixer()

    def test_date_normalization_yyyymmdd(self):
        self.assertEqual(self.fixer._normalize_date("20260503"), "2026-05-03")

    def test_date_normalization_yyyy_mm_dd(self):
        self.assertEqual(self.fixer._normalize_date("2026/05/03"), "2026-05-03")

    def test_date_normalization_yyyy_dot_mm_dot_dd(self):
        self.assertEqual(self.fixer._normalize_date("2026.05.03"), "2026-05-03")

    def test_date_normalization_already_iso(self):
        self.assertEqual(self.fixer._normalize_date("2026-05-03"), "2026-05-03")

    def test_date_normalization_invalid_returns_none(self):
        self.assertIsNone(self.fixer._normalize_date("not-a-date"))
        self.assertIsNone(self.fixer._normalize_date(""))

    def test_date_normalization_invalid_date_returns_none(self):
        # Feb 30 doesn't exist
        self.assertIsNone(self.fixer._normalize_date("20260230"))

    def test_fix_empty_card(self):
        """An empty metadata dict should classify all required fields as manual."""
        card = {"metadata": {}, "body": ""}
        plan = self.fixer.analyze(card)
        # All required fields missing → most are manual
        self.assertGreater(len(plan.manual_fix_required), 0)

    def test_fix_card_with_none_metadata(self):
        """Card with None metadata should handle gracefully."""
        card = {"metadata": None, "body": ""}
        plan = self.fixer.analyze(card)
        # Should not crash — all issues will be in manual
        self.assertIsInstance(plan, FixPlan)

    def test_idempotent_fix(self):
        """Fixing an already-fixed card should produce no additional changes."""
        with tempfile.NamedTemporaryFile(mode="w", suffix=".md", delete=False, encoding="utf-8") as f:
            f.write(MISSING_DEFAULTS_MD)
            f.flush()
            card = SkillCardParser.parse(f.name)
        os.unlink(f.name)

        # Fix once
        fixed1 = self.fixer.fix(card, dry_run=False)
        # Fix again with the already-fixed card
        fixed2 = self.fixer.fix(fixed1.card, dry_run=False)

        # Second fix should have no changes for the already-fixed fields
        changed_fields_2 = {c["field"] for c in fixed2.changes}
        self.assertNotIn("priority", changed_fields_2)
        self.assertNotIn("version", changed_fields_2)
        self.assertNotIn("tags", changed_fields_2)


if __name__ == "__main__":
    unittest.main()
