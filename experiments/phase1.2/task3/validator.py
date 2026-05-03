"""
Skill Card Batch Validation Engine

Validates skill card markdown files with YAML frontmatter against a schema.
Supports batch scanning with per-file error isolation.
"""

import os
import re
import json
from dataclasses import dataclass, field, asdict
from enum import Enum
from typing import Optional
from pathlib import Path

try:
    import yaml
except ImportError:
    yaml = None


# ---------------------------------------------------------------------------
# Hardcoded schema (fallback when skill_card_schema.json is absent)
# ---------------------------------------------------------------------------

SKILL_CARD_SCHEMA = {
    "required_fields": {
        "id": {"type": str, "pattern": r"^sc-\d{8}-[\w-]+$"},
        "type": {"type": str, "enum": ["domain", "pattern", "workflow"]},
        "category": {"type": str, "enum": ["domains", "patterns", "workflows", "pending"]},
        "task_types": {"type": list, "item_type": str},
        "avg_reward": {"type": (int, float), "min": 0.0, "max": 1.0},
        "usage_count": {"type": int, "min": 0},
        "created": {"type": (str,), "pattern": r"^\d{4}-\d{2}-\d{2}$", "coerce": str},
        "updated": {"type": (str,), "pattern": r"^\d{4}-\d{2}-\d{2}$", "coerce": str},
        "status": {"type": str, "enum": ["active", "draft", "deprecated"]},
        "sources": {"type": list, "item_type": str},
    },
    "optional_fields": {
        "transfer_mode": {"type": str, "enum": ["direct", "indirect", "forbidden"]},
        "related_learnings": {"type": list, "item_type": str},
        "planning_hints": {"type": dict},
    },
}


# ---------------------------------------------------------------------------
# Data structures
# ---------------------------------------------------------------------------

class Severity(Enum):
    ERROR = "error"
    WARN = "warn"
    INFO = "info"


@dataclass
class Issue:
    severity: Severity
    field: str
    message: str

    def to_dict(self):
        return {"severity": self.severity.value, "field": self.field, "message": self.message}


@dataclass
class ValidationResult:
    path: str = ""
    status: str = ""  # "pass", "warn", "error"
    issues: list = field(default_factory=list)  # list of Issue dicts
    error: Optional[str] = None  # parsing-level error

    def to_dict(self):
        return {
            "path": self.path,
            "status": self.status,
            "issues": [i.to_dict() if isinstance(i, Issue) else i for i in self.issues],
            "error": self.error,
        }


@dataclass
class BatchResult:
    total: int = 0
    passed: int = 0
    warned: int = 0
    errored: int = 0
    results: list = field(default_factory=list)

    def to_dict(self):
        return {
            "total": self.total,
            "passed": self.passed,
            "warned": self.warned,
            "errored": self.errored,
            "results": [r.to_dict() if hasattr(r, "to_dict") else r for r in self.results],
        }


# ---------------------------------------------------------------------------
# Parser
# ---------------------------------------------------------------------------

class SkillCardParser:
    """Parse a skill-card markdown file with YAML frontmatter into a dict."""

    @staticmethod
    def parse(filepath: str) -> dict:
        """
        Returns {"metadata": {...}, "body": "..."} or raises ValueError.
        """
        with open(filepath, "r", encoding="utf-8") as f:
            content = f.read()

        # Extract YAML frontmatter
        fm_match = re.match(r"^---\s*\n(.*?)\n---\s*\n", content, re.DOTALL)
        if not fm_match:
            raise ValueError("No YAML frontmatter found (missing --- delimiters)")

        fm_text = fm_match.group(1)
        body = content[fm_match.end():]

        if yaml is not None:
            metadata = yaml.safe_load(fm_text)
        else:
            # Minimal fallback: not a full YAML parser, just fail gracefully
            raise ValueError("PyYAML not installed; cannot parse frontmatter")

        if not isinstance(metadata, dict):
            raise ValueError(f"Frontmatter must be a YAML mapping, got {type(metadata).__name__}")

        return {"metadata": metadata, "body": body}


# ---------------------------------------------------------------------------
# Single-card validator
# ---------------------------------------------------------------------------

class CardValidator:
    """Validate a single parsed card dict against the schema."""

    def __init__(self, schema: Optional[dict] = None):
        self.schema = schema or SKILL_CARD_SCHEMA

    def validate(self, card: dict) -> ValidationResult:
        """
        card: {"metadata": {...}, "body": "..."}  (output of SkillCardParser)
        Returns ValidationResult.
        """
        result = ValidationResult(path="")
        meta = card.get("metadata", {})

        if not isinstance(meta, dict):
            result.status = "error"
            result.issues.append(Issue(Severity.ERROR, "metadata", "metadata is not a dict").to_dict())
            return result

        # 1. Check required fields
        req = self.schema.get("required_fields", {})
        for fname, spec in req.items():
            if fname not in meta:
                result.issues.append(
                    Issue(Severity.ERROR, fname, f"Required field '{fname}' is missing").to_dict()
                )
                continue
            self._check_field(meta, fname, spec, result)

        # 2. Check optional fields (only warn)
        opt = self.schema.get("optional_fields", {})
        for fname, spec in opt.items():
            if fname in meta:
                self._check_field(meta, fname, spec, result, optional=True)

        # 3. Check body has expected sections
        body = card.get("body", "")
        self._check_body(body, result)

        # Determine status
        has_error = any(i["severity"] == "error" for i in result.issues)
        has_warn = any(i["severity"] == "warn" for i in result.issues)

        if has_error:
            result.status = "error"
        elif has_warn:
            result.status = "warn"
        else:
            result.status = "pass"

        return result

    def _check_field(self, meta, fname, spec, result, optional=False):
        value = meta[fname]

        # Coerce if needed (e.g. datetime.date → str)
        if "coerce" in spec:
            coerce_fn = spec["coerce"]
            if not isinstance(value, str):
                try:
                    value = coerce_fn(value)
                    meta[fname] = value  # update in place for downstream checks
                except Exception:
                    pass  # let type check catch it

        expected_type = spec.get("type")

        # Type check
        if expected_type is not None:
            # Normalize expected_type to always be a tuple for isinstance
            if not isinstance(expected_type, tuple):
                expected_type = (expected_type,)
            if not isinstance(value, expected_type):
                sev = Severity.WARN if optional else Severity.ERROR
                result.issues.append(
                    Issue(sev, fname,
                          f"Field '{fname}' expected type {expected_type}, got {type(value).__name__}").to_dict()
                )
                return  # skip further checks if type is wrong

        # Enum check
        if "enum" in spec and isinstance(value, str):
            if value not in spec["enum"]:
                result.issues.append(
                    Issue(Severity.ERROR, fname,
                          f"Field '{fname}' value '{value}' not in allowed enum {spec['enum']}").to_dict()
                )

        # Pattern check
        if "pattern" in spec and isinstance(value, str):
            if not re.match(spec["pattern"], value):
                result.issues.append(
                    Issue(Severity.ERROR, fname,
                          f"Field '{fname}' value '{value}' does not match pattern {spec['pattern']}").to_dict()
                )

        # Range check (min/max for numbers)
        if isinstance(value, (int, float)):
            if "min" in spec and value < spec["min"]:
                result.issues.append(
                    Issue(Severity.ERROR, fname,
                          f"Field '{fname}' value {value} below minimum {spec['min']}").to_dict()
                )
            if "max" in spec and value > spec["max"]:
                result.issues.append(
                    Issue(Severity.ERROR, fname,
                          f"Field '{fname}' value {value} above maximum {spec['max']}").to_dict()
                )

        # List item type check
        if isinstance(value, list) and "item_type" in spec:
            item_type = spec["item_type"]
            for idx, item in enumerate(value):
                if not isinstance(item, item_type):
                    result.issues.append(
                        Issue(Severity.ERROR, f"{fname}[{idx}]",
                              f"Item at index {idx} expected type {item_type.__name__}, got {type(item).__name__}").to_dict()
                    )

        # Non-empty list
        if isinstance(value, list) and len(value) == 0 and not optional:
            result.issues.append(
                Issue(Severity.WARN, fname, f"Field '{fname}' is an empty list").to_dict()
            )

    def _check_body(self, body, result):
        """Check that the body contains expected markdown sections."""
        if not body.strip():
            result.issues.append(
                Issue(Severity.WARN, "body", "Card body is empty").to_dict()
            )
            return

        # Expected top-level sections
        expected_sections = ["成功经验", "失败教训", "推荐工作流"]
        for section in expected_sections:
            if section not in body:
                result.issues.append(
                    Issue(Severity.INFO, "body",
                          f"Recommended section '{section}' not found in body").to_dict()
                )


# ---------------------------------------------------------------------------
# Batch validator
# ---------------------------------------------------------------------------

class BatchValidator:
    """Scan a directory of skill cards and validate each one."""

    def __init__(self, schema: Optional[dict] = None):
        self.validator = CardValidator(schema)
        self.parser = SkillCardParser()
        self._name_registry = {}  # name/id → path for duplicate detection

    def scan_directory(self, directory: str) -> BatchResult:
        """
        Recursively find all .md files under directory and validate each.
        Single file exceptions do not interrupt the batch.
        """
        batch = BatchResult()
        dir_path = Path(directory)

        if not dir_path.exists():
            batch.errored = 1
            batch.total = 1
            batch.results.append(ValidationResult(
                path=directory, status="error", error=f"Directory does not exist: {directory}"
            ).to_dict())
            return batch

        md_files = sorted(dir_path.rglob("*.md"))

        for md_file in md_files:
            filepath = str(md_file)
            try:
                card = self.parser.parse(filepath)
                result = self.validator.validate(card)
                result.path = filepath
            except Exception as e:
                result = ValidationResult(
                    path=filepath, status="error", error=str(e)
                )

            # Duplicate detection by card id
            meta = {}
            try:
                card_parsed = self.parser.parse(filepath)
                meta = card_parsed.get("metadata", {})
            except Exception:
                pass

            card_id = meta.get("id", "")
            card_title = self._extract_title(filepath, meta)
            if card_id:
                if card_id in self._name_registry:
                    result.issues.append(
                        Issue(Severity.WARN, "id",
                              f"Duplicate id '{card_id}' — also found in {self._name_registry[card_id]}").to_dict()
                    )
                    # Re-determine status
                    if result.status == "pass":
                        result.status = "warn"
                else:
                    self._name_registry[card_id] = filepath

            batch.results.append(result.to_dict())
            batch.total += 1
            if result.status == "pass":
                batch.passed += 1
            elif result.status == "warn":
                batch.warned += 1
            else:
                batch.errored += 1

        return batch

    def _extract_title(self, filepath, meta):
        """Try to extract a display name for the card."""
        # Try H1 from body
        try:
            with open(filepath, "r", encoding="utf-8") as f:
                for line in f:
                    if line.startswith("# "):
                        return line[2:].strip()
        except Exception:
            pass
        return meta.get("id", os.path.basename(filepath))


# ---------------------------------------------------------------------------
# CLI entry point
# ---------------------------------------------------------------------------

def main():
    import sys

    target = sys.argv[1] if len(sys.argv) > 1 else "/tmp/agent-skill-chain/skill-cards/"
    print(f"Scanning: {target}\n")

    bv = BatchValidator()
    result = bv.scan_directory(target)

    print(json.dumps(result.to_dict(), indent=2, ensure_ascii=False))
    print(f"\nSummary: {result.total} cards | {result.passed} passed | {result.warned} warned | {result.errored} errored")


if __name__ == "__main__":
    main()
