"""
Unit tests for reporter.py — ValidationReport class.

Tests cover:
- add_result / add_batch_result
- get_summary with all severity combinations
- get_by_category grouping
- get_cards_with_errors / get_cards_with_warnings filtering
- format_text output structure
- format_json output structure
- edge cases: empty report, parse errors, unknown categories
"""

import json
import os
import sys
import unittest
from pathlib import Path
from unittest.mock import patch

# Ensure local imports work
sys.path.insert(0, os.path.dirname(__file__))

from reporter import ValidationReport, generate_report


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _make_result(path, status, issues=None, error=None):
    """Build a validation result dict."""
    return {
        "path": path,
        "status": status,
        "issues": issues or [],
        "error": error,
    }


def _make_issue(severity, field, message):
    return {"severity": severity, "field": field, "message": message}


def _sample_batch_dict(results=None, total=0, passed=0, warned=0, errored=0):
    """Build a BatchResult-like dict."""
    return {
        "total": total,
        "passed": passed,
        "warned": warned,
        "errored": errored,
        "results": results or [],
    }


# ---------------------------------------------------------------------------
# Test Cases
# ---------------------------------------------------------------------------

class TestAddResult(unittest.TestCase):
    """Tests for add_result and add_batch_result."""

    def test_add_dict_result(self):
        report = ValidationReport()
        report.add_result("cards/a.md", _make_result("cards/a.md", "pass"))
        self.assertEqual(len(report._results), 1)
        self.assertEqual(report._results[0]["status"], "pass")

    def test_add_result_fills_missing_path(self):
        report = ValidationReport()
        entry = _make_result("", "pass")
        report.add_result("cards/b.md", entry)
        self.assertEqual(report._results[0]["path"], "cards/b.md")

    def test_add_result_with_object(self):
        """Test adding an object with .to_dict() method."""
        class FakeResult:
            def to_dict(self):
                return {"path": "x.md", "status": "warn", "issues": [], "error": None}

        report = ValidationReport()
        report.add_result("x.md", FakeResult())
        self.assertEqual(len(report._results), 1)
        self.assertEqual(report._results[0]["status"], "warn")

    def test_add_result_with_non_dict_non_object(self):
        """Test adding a plain string (should be wrapped as error)."""
        report = ValidationReport()
        report.add_result("bad.md", "something went wrong")
        self.assertEqual(len(report._results), 1)
        self.assertEqual(report._results[0]["status"], "error")
        self.assertEqual(report._results[0]["error"], "something went wrong")

    def test_add_batch_result_dict(self):
        report = ValidationReport()
        batch = _sample_batch_dict(
            results=[
                _make_result("a.md", "pass"),
                _make_result("b.md", "error", [_make_issue("error", "id", "missing")]),
            ],
            total=2, passed=1, warned=0, errored=1,
        )
        report.add_batch_result(batch)
        self.assertEqual(len(report._results), 2)

    def test_add_batch_result_object(self):
        class FakeBatch:
            def to_dict(self):
                return {"results": [_make_result("z.md", "pass")]}

        report = ValidationReport()
        report.add_batch_result(FakeBatch())
        self.assertEqual(len(report._results), 1)

    def test_add_batch_result_invalid_type(self):
        report = ValidationReport()
        with self.assertRaises(TypeError):
            report.add_batch_result(42)


class TestGetSummary(unittest.TestCase):
    """Tests for get_summary()."""

    def test_empty_report(self):
        report = ValidationReport()
        s = report.get_summary()
        self.assertEqual(s["total"], 0)
        self.assertEqual(s["passed"], 0)
        self.assertEqual(s["warnings"], 0)
        self.assertEqual(s["errors"], 0)
        self.assertEqual(s["error_breakdown_by_type"], {})

    def test_all_passed(self):
        report = ValidationReport()
        for i in range(5):
            report.add_result(f"cards/{i}.md", _make_result(f"cards/{i}.md", "pass"))
        s = report.get_summary()
        self.assertEqual(s["total"], 5)
        self.assertEqual(s["passed"], 5)
        self.assertEqual(s["warnings"], 0)
        self.assertEqual(s["errors"], 0)

    def test_mixed_severities(self):
        report = ValidationReport()
        report.add_result("a.md", _make_result("a.md", "pass"))
        report.add_result("b.md", _make_result("b.md", "warn",
                         [_make_issue("warn", "body", "empty")]))
        report.add_result("c.md", _make_result("c.md", "error",
                         [_make_issue("error", "id", "missing"),
                          _make_issue("error", "category", "invalid")]))
        report.add_result("d.md", _make_result("d.md", "error",
                         [_make_issue("error", "id", "duplicate")]))
        s = report.get_summary()
        self.assertEqual(s["total"], 4)
        self.assertEqual(s["passed"], 1)
        self.assertEqual(s["warnings"], 1)
        self.assertEqual(s["errors"], 2)
        self.assertEqual(s["error_breakdown_by_type"]["id"], 2)
        self.assertEqual(s["error_breakdown_by_type"]["category"], 1)

    def test_error_breakdown_excludes_non_errors(self):
        report = ValidationReport()
        report.add_result("a.md", _make_result("a.md", "warn",
                         [_make_issue("warn", "body", "empty"),
                          _make_issue("info", "body", "missing section")]))
        s = report.get_summary()
        self.assertEqual(s["error_breakdown_by_type"], {})

    def test_cards_with_parse_error_counted(self):
        report = ValidationReport()
        report.add_result("bad.md", _make_result("bad.md", "error", error="YAML parse failed"))
        s = report.get_summary()
        self.assertEqual(s["errors"], 1)
        self.assertEqual(s["passed"], 0)


class TestGetByCategory(unittest.TestCase):
    """Tests for get_by_category()."""

    def test_single_category(self):
        report = ValidationReport()
        report.add_result("skill-cards/patterns/a.md", _make_result("skill-cards/patterns/a.md", "pass"))
        report.add_result("skill-cards/patterns/b.md", _make_result("skill-cards/patterns/b.md", "warn"))
        by_cat = report.get_by_category()
        self.assertIn("patterns", by_cat)
        self.assertEqual(by_cat["patterns"]["total"], 2)
        self.assertEqual(by_cat["patterns"]["passed"], 1)
        self.assertEqual(by_cat["patterns"]["warnings"], 1)

    def test_multiple_categories(self):
        report = ValidationReport()
        report.add_result("cards/patterns/a.md", _make_result("cards/patterns/a.md", "pass"))
        report.add_result("cards/domains/b.md", _make_result("cards/domains/b.md", "error",
                         [_make_issue("error", "name", "too short")]))
        report.add_result("cards/workflows/c.md", _make_result("cards/workflows/c.md", "pass"))
        by_cat = report.get_by_category()
        self.assertEqual(len(by_cat), 3)
        self.assertIn("patterns", by_cat)
        self.assertIn("domains", by_cat)
        self.assertIn("workflows", by_cat)

    def test_pending_category(self):
        report = ValidationReport()
        report.add_result("cards/pending/draft.md", _make_result("cards/pending/draft.md", "pass"))
        by_cat = report.get_by_category()
        self.assertIn("pending", by_cat)

    def test_uncategorized_fallback(self):
        report = ValidationReport()
        report.add_result("some_random_dir/card.md", _make_result("some_random_dir/card.md", "pass"))
        by_cat = report.get_by_category()
        # Should use parent dir name as category
        self.assertTrue(len(by_cat) > 0)
        cat_name = list(by_cat.keys())[0]
        self.assertEqual(cat_name, "some_random_dir")

    def test_category_cards_list(self):
        report = ValidationReport()
        report.add_result("cards/patterns/a.md", _make_result("cards/patterns/a.md", "pass"))
        by_cat = report.get_by_category()
        self.assertEqual(len(by_cat["patterns"]["cards"]), 1)
        self.assertEqual(by_cat["patterns"]["cards"][0]["path"], "cards/patterns/a.md")


class TestGetCardsWithErrors(unittest.TestCase):
    """Tests for get_cards_with_errors() and get_cards_with_warnings()."""

    def test_no_errors(self):
        report = ValidationReport()
        report.add_result("a.md", _make_result("a.md", "pass"))
        self.assertEqual(report.get_cards_with_errors(), [])

    def test_filters_errors(self):
        report = ValidationReport()
        report.add_result("a.md", _make_result("a.md", "pass"))
        report.add_result("b.md", _make_result("b.md", "error", [_make_issue("error", "id", "bad")]))
        report.add_result("c.md", _make_result("c.md", "warn"))
        errs = report.get_cards_with_errors()
        self.assertEqual(len(errs), 1)
        self.assertEqual(errs[0]["path"], "b.md")

    def test_filters_warnings(self):
        report = ValidationReport()
        report.add_result("a.md", _make_result("a.md", "pass"))
        report.add_result("b.md", _make_result("b.md", "warn", [_make_issue("warn", "body", "empty")]))
        warns = report.get_cards_with_warnings()
        self.assertEqual(len(warns), 1)
        self.assertEqual(warns[0]["path"], "b.md")

    def test_multiple_errors(self):
        report = ValidationReport()
        for i in range(3):
            report.add_result(f"e{i}.md", _make_result(f"e{i}.md", "error"))
        for i in range(2):
            report.add_result(f"p{i}.md", _make_result(f"p{i}.md", "pass"))
        self.assertEqual(len(report.get_cards_with_errors()), 3)


class TestFormatText(unittest.TestCase):
    """Tests for format_text()."""

    def test_empty_report(self):
        report = ValidationReport()
        text = report.format_text()
        self.assertIn("Total: 0", text)
        self.assertIn("Passed: 0", text)
        self.assertIn("Errors: 0", text)

    def test_contains_summary(self):
        report = ValidationReport()
        report.add_result("cards/patterns/a.md", _make_result("cards/patterns/a.md", "pass"))
        report.add_result("cards/patterns/b.md", _make_result("cards/patterns/b.md", "error",
                         [_make_issue("error", "id", "missing")]))
        text = report.format_text()
        self.assertIn("Total: 2", text)
        self.assertIn("Passed: 1", text)
        self.assertIn("Errors: 1", text)

    def test_contains_category_section(self):
        report = ValidationReport()
        report.add_result("cards/patterns/a.md", _make_result("cards/patterns/a.md", "pass"))
        text = report.format_text()
        self.assertIn("By Category", text)
        self.assertIn("[patterns]", text)

    def test_shows_error_breakdown(self):
        report = ValidationReport()
        report.add_result("a.md", _make_result("a.md", "error",
                         [_make_issue("error", "id", "bad format"),
                          _make_issue("error", "id", "also bad")]))
        text = report.format_text()
        self.assertIn("Error breakdown by field", text)
        self.assertIn("id", text)

    def test_shows_issue_details(self):
        report = ValidationReport()
        report.add_result("cards/patterns/a.md", _make_result("cards/patterns/a.md", "warn",
                         [_make_issue("warn", "body", "empty body")]))
        text = report.format_text()
        self.assertIn("body", text)
        self.assertIn("empty body", text)

    def test_shows_parse_error(self):
        report = ValidationReport()
        report.add_result("bad.md", _make_result("bad.md", "error", error="YAML parse failed"))
        text = report.format_text()
        self.assertIn("PARSE ERROR", text)
        self.assertIn("YAML parse failed", text)

    def test_custom_title(self):
        report = ValidationReport()
        text = report.format_text(title="Custom Report Title")
        self.assertIn("Custom Report Title", text)

    def test_pass_icon(self):
        report = ValidationReport()
        report.add_result("cards/patterns/a.md", _make_result("cards/patterns/a.md", "pass"))
        text = report.format_text()
        self.assertIn("✅", text)

    def test_warn_icon(self):
        report = ValidationReport()
        report.add_result("cards/patterns/a.md", _make_result("cards/patterns/a.md", "warn",
                         [_make_issue("warn", "f", "msg")]))
        text = report.format_text()
        self.assertIn("⚠️", text)

    def test_error_icon(self):
        report = ValidationReport()
        report.add_result("cards/patterns/a.md", _make_result("cards/patterns/a.md", "error",
                         [_make_issue("error", "f", "msg")]))
        text = report.format_text()
        self.assertIn("❌", text)


class TestFormatJson(unittest.TestCase):
    """Tests for format_json()."""

    def test_structure(self):
        report = ValidationReport()
        report.add_result("cards/patterns/a.md", _make_result("cards/patterns/a.md", "pass"))
        j = report.format_json()
        self.assertIn("title", j)
        self.assertIn("summary", j)
        self.assertIn("by_category", j)
        self.assertIn("cards_with_errors", j)
        self.assertIn("all_results", j)

    def test_json_serializable(self):
        report = ValidationReport()
        report.add_result("a.md", _make_result("a.md", "error",
                         [_make_issue("error", "id", "bad")]))
        j = report.format_json()
        # Must not raise
        serialized = json.dumps(j, ensure_ascii=False)
        self.assertIsInstance(serialized, str)

    def test_summary_matches(self):
        report = ValidationReport()
        report.add_result("a.md", _make_result("a.md", "pass"))
        report.add_result("b.md", _make_result("b.md", "error", [_make_issue("error", "x", "y")]))
        j = report.format_json()
        self.assertEqual(j["summary"]["total"], 2)
        self.assertEqual(j["summary"]["passed"], 1)
        self.assertEqual(j["summary"]["errors"], 1)

    def test_cards_with_errors_populated(self):
        report = ValidationReport()
        report.add_result("bad.md", _make_result("bad.md", "error", [_make_issue("error", "f", "m")]))
        report.add_result("good.md", _make_result("good.md", "pass"))
        j = report.format_json()
        self.assertEqual(len(j["cards_with_errors"]), 1)
        self.assertEqual(j["cards_with_errors"][0]["path"], "bad.md")

    def test_all_results_included(self):
        report = ValidationReport()
        for i in range(3):
            report.add_result(f"{i}.md", _make_result(f"{i}.md", "pass"))
        j = report.format_json()
        self.assertEqual(len(j["all_results"]), 3)


class TestExtractCategory(unittest.TestCase):
    """Tests for the _extract_category static method."""

    def test_patterns(self):
        self.assertEqual(ValidationReport._extract_category("skill-cards/patterns/a.md"), "patterns")

    def test_domains(self):
        self.assertEqual(ValidationReport._extract_category("skill-cards/domains/b.md"), "domains")

    def test_workflows(self):
        self.assertEqual(ValidationReport._extract_category("skill-cards/workflows/c.md"), "workflows")

    def test_pending(self):
        self.assertEqual(ValidationReport._extract_category("skill-cards/pending/d.md"), "pending")

    def test_nested_path(self):
        self.assertEqual(ValidationReport._extract_category("/a/b/c/patterns/deep/e.md"), "patterns")

    def test_unknown_uses_parent(self):
        cat = ValidationReport._extract_category("some_folder/file.md")
        self.assertEqual(cat, "some_folder")

    def test_empty_path(self):
        cat = ValidationReport._extract_category("")
        # Should not crash
        self.assertIsInstance(cat, str)


class TestGenerateReport(unittest.TestCase):
    """Integration test for generate_report() against the real skill-cards directory."""

    SKILL_CARDS_DIR = "/tmp/agent-skill-chain/skill-cards/"

    @unittest.skipUnless(os.path.isdir(SKILL_CARDS_DIR), "skill-cards directory not available")
    def test_text_report_runs(self):
        output = generate_report(self.SKILL_CARDS_DIR, "text")
        self.assertIsInstance(output, str)
        self.assertIn("Total:", output)

    @unittest.skipUnless(os.path.isdir(SKILL_CARDS_DIR), "skill-cards directory not available")
    def test_json_report_runs(self):
        output = generate_report(self.SKILL_CARDS_DIR, "json")
        data = json.loads(output)
        self.assertIn("summary", data)
        self.assertGreater(data["summary"]["total"], 0)

    @unittest.skipUnless(os.path.isdir(SKILL_CARDS_DIR), "skill-cards directory not available")
    def test_report_matches_known_card_count(self):
        output = generate_report(self.SKILL_CARDS_DIR, "json")
        data = json.loads(output)
        # We know there are 12 cards from the validator engine step
        self.assertEqual(data["summary"]["total"], 12)

    def test_nonexistent_directory(self):
        output = generate_report("/tmp/nonexistent_skill_cards_xyz/", "text")
        self.assertIsInstance(output, str)
        # Should still produce a report (with error)
        self.assertIn("Total:", output)


if __name__ == "__main__":
    unittest.main()
