"""
Skill Card Batch Validation Report Generator

Consumes validation results (BatchResult or list of ValidationResult dicts)
and produces structured reports with severity breakdown, category grouping,
and multiple output formats (text, JSON).
"""

import json
import os
from collections import defaultdict
from dataclasses import dataclass, field, asdict
from pathlib import Path
from typing import Optional, Dict, List, Any

# Re-use validator types if imported together; otherwise define lightweight versions.
try:
    from validator import BatchValidator, ValidationResult, Severity
except ImportError:
    # Standalone fallback — minimal definitions
    class Severity:
        ERROR = "error"
        WARN = "warn"
        INFO = "info"


# ---------------------------------------------------------------------------
# ValidationReport — core aggregation class
# ---------------------------------------------------------------------------

class ValidationReport:
    """
    Aggregates per-card validation results into a queryable report.

    Usage:
        report = ValidationReport()
        for card_path, result in results:
            report.add_result(card_path, result)
        print(report.format_text())
    """

    def __init__(self):
        self._results: List[Dict[str, Any]] = []

    # ------------------------------------------------------------------
    # Mutation
    # ------------------------------------------------------------------

    def add_result(self, card_path: str, validation_result: Any) -> None:
        """
        Add a single card's validation result.

        Args:
            card_path: Filesystem path (or relative key) for the card.
            validation_result: Either a ValidationResult object (with .to_dict())
                               or a plain dict with keys: path, status, issues, error.
        """
        if hasattr(validation_result, "to_dict"):
            entry = validation_result.to_dict()
        elif isinstance(validation_result, dict):
            entry = dict(validation_result)
        else:
            entry = {"path": card_path, "status": "error", "issues": [], "error": str(validation_result)}

        # Ensure path is set
        if not entry.get("path"):
            entry["path"] = card_path

        self._results.append(entry)

    def add_batch_result(self, batch_result: Any) -> None:
        """
        Add all results from a BatchResult object.

        Args:
            batch_result: BatchResult with .results list, or a dict with "results" key.
        """
        if hasattr(batch_result, "to_dict"):
            data = batch_result.to_dict()
        elif isinstance(batch_result, dict):
            data = batch_result
        else:
            raise TypeError(f"Unsupported batch_result type: {type(batch_result)}")

        for entry in data.get("results", []):
            self._results.append(entry)

    # ------------------------------------------------------------------
    # Queries
    # ------------------------------------------------------------------

    def get_summary(self) -> Dict[str, Any]:
        """
        Overall statistics.

        Returns:
            {
                "total": int,
                "passed": int,
                "warnings": int,
                "errors": int,
                "error_breakdown_by_type": {field: count, ...}
            }
        """
        total = len(self._results)
        passed = 0
        warnings = 0
        errors = 0
        error_breakdown: Dict[str, int] = defaultdict(int)

        for entry in self._results:
            status = entry.get("status", "error")
            if status == "pass":
                passed += 1
            elif status == "warn":
                warnings += 1
            elif status == "error":
                errors += 1

            # Count error-level issues by field
            for issue in entry.get("issues", []):
                sev = issue.get("severity", "")
                if sev == "error":
                    error_breakdown[issue.get("field", "unknown")] += 1

        return {
            "total": total,
            "passed": passed,
            "warnings": warnings,
            "errors": errors,
            "error_breakdown_by_type": dict(error_breakdown),
        }

    def get_by_category(self) -> Dict[str, Dict[str, Any]]:
        """
        Group results by category (derived from the file path).

        The category is extracted from the path segment immediately under
        the skill-cards root directory (e.g. "patterns", "domains", "workflows", "pending").

        Returns:
            {
                "patterns": {"total": N, "passed": N, "warnings": N, "errors": N, "cards": [...]},
                ...
            }
        """
        groups: Dict[str, Dict[str, Any]] = {}

        for entry in self._results:
            category = self._extract_category(entry.get("path", ""))
            if category not in groups:
                groups[category] = {
                    "total": 0,
                    "passed": 0,
                    "warnings": 0,
                    "errors": 0,
                    "cards": [],
                }
            g = groups[category]
            g["total"] += 1
            g["cards"].append(entry)

            status = entry.get("status", "error")
            if status == "pass":
                g["passed"] += 1
            elif status == "warn":
                g["warnings"] += 1
            else:
                g["errors"] += 1

        return groups

    def get_cards_with_errors(self) -> List[Dict[str, Any]]:
        """Return only cards that have status 'error'."""
        return [e for e in self._results if e.get("status") == "error"]

    def get_cards_with_warnings(self) -> List[Dict[str, Any]]:
        """Return only cards that have status 'warn'."""
        return [e for e in self._results if e.get("status") == "warn"]

    # ------------------------------------------------------------------
    # Output formatters
    # ------------------------------------------------------------------

    def format_text(self, title: str = "Skill Card Validation Report") -> str:
        """
        Human-readable multi-line text report.

        Layout:
            ── Title ──
            Summary: total / passed / warnings / errors
            ── By Category ──
              patterns (N cards)
                ✅ card-a.md  — pass
                ⚠️  card-b.md  — warn: [issue list]
                ❌ card-c.md  — error: [issue list]
              ...
        """
        lines: List[str] = []
        sep = "=" * 60

        summary = self.get_summary()

        # Header
        lines.append(sep)
        lines.append(f"  {title}")
        lines.append(sep)
        lines.append("")

        # Summary
        lines.append(f"Total: {summary['total']}  |  ✅ Passed: {summary['passed']}  "
                     f"|  ⚠️  Warnings: {summary['warnings']}  |  ❌ Errors: {summary['errors']}")
        if summary["error_breakdown_by_type"]:
            lines.append("")
            lines.append("Error breakdown by field:")
            for fname, count in sorted(summary["error_breakdown_by_type"].items(), key=lambda x: -x[1]):
                lines.append(f"  - {fname}: {count}")
        lines.append("")

        # By category
        by_cat = self.get_by_category()
        if by_cat:
            lines.append("-" * 40)
            lines.append("By Category")
            lines.append("-" * 40)
            for cat in sorted(by_cat.keys()):
                g = by_cat[cat]
                lines.append("")
                lines.append(f"  [{cat}]  {g['total']} cards — "
                             f"✅ {g['passed']}  ⚠️  {g['warnings']}  ❌ {g['errors']}")
                for card in g["cards"]:
                    card_name = os.path.basename(card.get("path", "unknown"))
                    status = card.get("status", "error")
                    icon = {"pass": "✅", "warn": "⚠️ ", "error": "❌"}.get(status, "?")
                    line = f"    {icon} {card_name}"
                    issues = card.get("issues", [])
                    if issues:
                        issue_summaries = []
                        for iss in issues:
                            sev = iss.get("severity", "info")
                            fld = iss.get("field", "?")
                            msg = iss.get("message", "")
                            tag = {"error": "E", "warn": "W", "info": "I"}.get(sev, "?")
                            issue_summaries.append(f"[{tag}] {fld}: {msg}")
                        line += "  — " + "; ".join(issue_summaries)
                    parse_err = card.get("error")
                    if parse_err:
                        line += f"  — PARSE ERROR: {parse_err}"
                    lines.append(line)

        lines.append("")
        lines.append(sep)
        return "\n".join(lines)

    def format_json(self, title: str = "Skill Card Validation Report") -> Dict[str, Any]:
        """
        Structured JSON-serializable report.

        Returns a dict suitable for json.dumps().
        """
        return {
            "title": title,
            "summary": self.get_summary(),
            "by_category": self.get_by_category(),
            "cards_with_errors": self.get_cards_with_errors(),
            "all_results": self._results,
        }

    # ------------------------------------------------------------------
    # Internals
    # ------------------------------------------------------------------

    @staticmethod
    def _extract_category(path: str) -> str:
        """
        Derive a category key from the file path.

        Tries to find a segment like 'patterns', 'domains', 'workflows', 'pending'
        in the path. Falls back to 'uncategorized'.
        """
        known_categories = {"patterns", "domains", "workflows", "pending"}
        parts = Path(path).parts
        for part in parts:
            if part.lower() in known_categories:
                return part.lower()
        # Fallback: parent directory name
        parent = Path(path).parent.name
        return parent if parent else "uncategorized"


# ---------------------------------------------------------------------------
# CLI helper — run full pipeline and output report
# ---------------------------------------------------------------------------

def generate_report(directory: str, output_format: str = "text") -> str:
    """
    Scan directory, validate all cards, and return formatted report.

    Args:
        directory: Path to skill-cards directory.
        output_format: "text" or "json".

    Returns:
        Formatted report string.
    """
    from validator import BatchValidator

    bv = BatchValidator()
    batch = bv.scan_directory(directory)

    report = ValidationReport()
    report.add_batch_result(batch)

    if output_format == "json":
        return json.dumps(report.format_json(), indent=2, ensure_ascii=False)
    else:
        return report.format_text()


def main():
    import sys

    directory = sys.argv[1] if len(sys.argv) > 1 else "/tmp/agent-skill-chain/skill-cards/"
    fmt = sys.argv[2] if len(sys.argv) > 2 else "text"

    output = generate_report(directory, fmt)
    print(output)


if __name__ == "__main__":
    main()
