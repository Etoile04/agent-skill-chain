"""
Skill Card Auto-Fix Engine

Automatically repairs fixable issues in skill cards and re-validates.
Supports dry-run mode and file backup.
"""

import os
import re
import json
import copy
import shutil
from dataclasses import dataclass, field
from datetime import datetime
from typing import Optional, List, Dict, Any

from validator import CardValidator, SkillCardParser, ValidationResult


# ---------------------------------------------------------------------------
# Data structures
# ---------------------------------------------------------------------------

@dataclass
class FixAction:
    """A single fix action applied to a field."""
    field: str
    issue: str          # original issue description
    action: str         # what was done (e.g. "set default 'medium'")
    old_value: Any = None
    new_value: Any = None

    def to_dict(self):
        return {
            "field": self.field,
            "issue": self.issue,
            "action": self.action,
            "old_value": self.old_value,
            "new_value": self.new_value,
        }


@dataclass
class FixPlan:
    """Plan of fixable and unfixable issues for a card."""
    fixable: List[Dict] = field(default_factory=list)
    manual_fix_required: List[Dict] = field(default_factory=list)

    def to_dict(self):
        return {
            "fixable": self.fixable,
            "manual_fix_required": self.manual_fix_required,
        }


@dataclass
class FixedCard:
    """Result of fixing a card dict."""
    card: Dict = field(default_factory=dict)
    changes: List[Dict] = field(default_factory=list)  # list of FixAction dicts
    revalidation: Optional[Dict] = None  # ValidationResult.to_dict()

    def to_dict(self):
        return {
            "card": self.card,
            "changes": self.changes,
            "revalidation": self.revalidation,
        }


@dataclass
class FixResult:
    """Result of fixing a file."""
    path: str = ""
    success: bool = False
    dry_run: bool = False
    backup_path: Optional[str] = None
    fixed_card: Optional[Dict] = None  # FixedCard.to_dict()
    error: Optional[str] = None

    def to_dict(self):
        return {
            "path": self.path,
            "success": self.success,
            "dry_run": self.dry_run,
            "backup_path": self.backup_path,
            "fixed_card": self.fixed_card,
            "error": self.error,
        }


# ---------------------------------------------------------------------------
# Default values for fillable fields
# ---------------------------------------------------------------------------

# Fields that have auto-fill defaults when missing entirely
FILL_DEFAULTS = {
    "priority": "medium",
    "version": "0.1.0",
    "tags": [],
    "related_cards": [],
    "transfer_mode": "direct",
    "related_learnings": [],
    "planning_hints": {},
}

# ISO 8601 date pattern (YYYY-MM-DD)
ISO_DATE_RE = re.compile(r"^\d{4}-\d{2}-\d{2}$")


# ---------------------------------------------------------------------------
# AutoFixer
# ---------------------------------------------------------------------------

class AutoFixer:
    """Analyze and auto-fix skill card issues."""

    def __init__(self, validator: Optional[CardValidator] = None):
        self.validator = validator or CardValidator()

    # ------------------------------------------------------------------
    # analyze — detect all fixable and unfixable issues
    # ------------------------------------------------------------------
    def analyze(self, card_dict: Dict) -> FixPlan:
        """
        Analyze a card dict ({"metadata": {...}, "body": "..."}) and return
        a FixPlan separating fixable from manual-fix-required issues.

        Scans both:
        1. Issues reported by the validator
        2. Missing optional fields that have known defaults
        3. Detectable quality issues (whitespace, empty strings, non-ISO dates)
        """
        plan = FixPlan()
        meta = card_dict.get("metadata") or {}
        result = self.validator.validate(copy.deepcopy(card_dict))

        # 1. Collect validator-reported issues
        for issue in result.issues:
            sev = issue["severity"]
            fname = issue["field"]
            msg = issue["message"]

            fixable = self._classify_validator_issue(meta, fname, msg, sev)
            entry = {"severity": sev, "field": fname, "message": msg, "fixable": fixable}

            if fixable:
                plan.fixable.append(entry)
            else:
                plan.manual_fix_required.append(entry)

        # 2. Scan for missing optional fields with defaults
        already_in_plan = {e["field"] for e in plan.fixable + plan.manual_fix_required}
        for fname, default_val in FILL_DEFAULTS.items():
            if fname not in meta and fname not in already_in_plan:
                plan.fixable.append({
                    "severity": "warn",
                    "field": fname,
                    "message": f"Optional field '{fname}' is missing",
                    "fixable": True,
                })

        # 3. Scan for quality issues in existing fields
        self._scan_quality_issues(meta, plan)

        return plan

    def _classify_validator_issue(self, meta: Dict, field_name: str, message: str, severity: str) -> bool:
        """Determine if a validator-reported issue is auto-fixable."""
        if severity == "error":
            # Missing required fields that have defaults
            if "is missing" in message:
                return field_name in FILL_DEFAULTS

            # Date format issues
            if field_name in ("created", "updated", "created_at", "updated_at"):
                if "does not match pattern" in message:
                    return True

            # Type mismatches, enum violations, pattern violations → manual
            return False

        if severity == "warn":
            if "empty list" in message.lower():
                return True
            if field_name == "description":
                return True
            return False

        return False  # info-level

    def _scan_quality_issues(self, meta: Dict, plan: FixPlan):
        """Scan metadata for quality issues not necessarily caught by validator."""
        planned_fields = {e["field"] for e in plan.fixable + plan.manual_fix_required}

        for fname, value in meta.items():
            # --- Description whitespace ---
            if fname == "description" and isinstance(value, str):
                if value != value.strip():
                    key = f"{fname}__whitespace"
                    if key not in planned_fields:
                        plan.fixable.append({
                            "severity": "warn",
                            "field": fname,
                            "message": f"Field '{fname}' has leading/trailing whitespace",
                            "fixable": True,
                        })

            # --- Non-ISO date fields ---
            if fname in ("created", "updated", "created_at", "updated_at"):
                # Handle both string and int (YAML parses 20260503 as int)
                date_str = str(value) if isinstance(value, int) else value
                if isinstance(date_str, str) and not ISO_DATE_RE.match(date_str):
                    key = fname
                    if not any(e["field"] == fname for e in plan.fixable):
                        plan.fixable.append({
                            "severity": "warn",
                            "field": fname,
                            "message": f"Field '{fname}' date '{value}' is not ISO 8601",
                            "fixable": True,
                        })

            # --- Array fields with empty strings ---
            if isinstance(value, list) and fname in (
                "tags", "when_to_use", "common_failures", "sources",
                "related_cards", "related_learnings", "task_types",
            ):
                empty_count = sum(1 for item in value if item == "")
                if empty_count > 0:
                    if not any(e["field"] == fname and "empty string" in e["message"] for e in plan.fixable):
                        plan.fixable.append({
                            "severity": "warn",
                            "field": fname,
                            "message": f"Field '{fname}' contains {empty_count} empty string(s)",
                            "fixable": True,
                        })

    # ------------------------------------------------------------------
    # fix — in-memory fix
    # ------------------------------------------------------------------
    def fix(self, card_dict: Dict, dry_run: bool = False) -> FixedCard:
        """
        Fix a card dict in memory. Returns FixedCard with changes list.
        If dry_run=True, returns a preview without modifying the original.
        """
        plan = self.analyze(card_dict)

        if dry_run:
            preview_card = copy.deepcopy(card_dict)
            changes = self._apply_fixes(preview_card, plan.fixable)
            return FixedCard(
                card=preview_card,
                changes=[c.to_dict() for c in changes],
                revalidation=None,
            )

        # Real fix
        fixed = copy.deepcopy(card_dict)
        changes = self._apply_fixes(fixed, plan.fixable)

        # Re-validate
        reval = self.validator.validate(fixed)
        revalidation = reval.to_dict()

        return FixedCard(
            card=fixed,
            changes=[c.to_dict() for c in changes],
            revalidation=revalidation,
        )

    def _apply_fixes(self, card: Dict, fixable_issues: List[Dict]) -> List[FixAction]:
        """Apply fix actions to a card dict in-place. Returns list of FixAction."""
        changes = []
        meta = card.get("metadata")
        if meta is None:
            card["metadata"] = {}
            meta = card["metadata"]

        applied = set()  # track (field, fix_type) to avoid duplicates

        for issue in fixable_issues:
            fname = issue["field"]
            msg = issue["message"]

            # --- Missing field → fill default ---
            if "is missing" in msg or "Optional field" in msg:
                fix_key = (fname, "default")
                if fname not in meta and fix_key not in applied and fname in FILL_DEFAULTS:
                    default_val = FILL_DEFAULTS[fname]
                    meta[fname] = default_val
                    changes.append(FixAction(
                        field=fname,
                        issue=msg,
                        action=f"set default '{default_val}'",
                        old_value=None,
                        new_value=default_val,
                    ))
                    applied.add(fix_key)

            # --- Date format normalization ---
            if "not ISO 8601" in msg or "does not match pattern" in msg:
                fix_key = (fname, "date")
                if fname in meta and fix_key not in applied:
                    val = meta[fname]
                    # Handle int dates (YAML parses 20260503 as int)
                    val_str = str(val) if isinstance(val, int) else val
                    if isinstance(val_str, str) and not ISO_DATE_RE.match(val_str):
                        normalized = self._normalize_date(val_str)
                        if normalized:
                            old = meta[fname]
                            meta[fname] = normalized
                            changes.append(FixAction(
                                field=fname,
                                issue=msg,
                                action=f"normalized date '{val}' → '{normalized}'",
                                old_value=old,
                                new_value=normalized,
                            ))
                            applied.add(fix_key)

            # --- Trim description whitespace ---
            if "whitespace" in msg.lower() and fname == "description":
                fix_key = (fname, "trim")
                if fname in meta and fix_key not in applied:
                    val = meta[fname]
                    if isinstance(val, str) and val != val.strip():
                        old = meta[fname]
                        meta[fname] = val.strip()
                        changes.append(FixAction(
                            field=fname,
                            issue=msg,
                            action="trimmed leading/trailing whitespace",
                            old_value=old,
                            new_value=meta[fname],
                        ))
                        applied.add(fix_key)

            # --- Filter empty strings from arrays ---
            if "empty string" in msg.lower():
                fix_key = (fname, "filter_empty")
                if fname in meta and fix_key not in applied:
                    val = meta[fname]
                    if isinstance(val, list):
                        filtered = [item for item in val if item != ""]
                        if len(filtered) != len(val):
                            old = meta[fname]
                            meta[fname] = filtered
                            changes.append(FixAction(
                                field=fname,
                                issue=msg,
                                action=f"filtered {len(val) - len(filtered)} empty string(s) from array",
                                old_value=old,
                                new_value=filtered,
                            ))
                            applied.add(fix_key)

        return changes

    def _normalize_date(self, date_str: str) -> Optional[str]:
        """
        Try to normalize a date string to YYYY-MM-DD (ISO 8601).
        Returns None if cannot be auto-fixed.
        """
        if ISO_DATE_RE.match(date_str):
            return date_str

        # YYYY/MM/DD or YYYY.MM.DD
        match = re.match(r"^(\d{4})[./](\d{1,2})[./](\d{1,2})$", date_str)
        if match:
            y, m, d = int(match.group(1)), int(match.group(2)), int(match.group(3))
            try:
                datetime(y, m, d)
                return f"{y:04d}-{m:02d}-{d:02d}"
            except ValueError:
                return None

        # YYYYMMDD (no separators)
        match = re.match(r"^(\d{4})(\d{2})(\d{2})$", date_str)
        if match:
            y, m, d = int(match.group(1)), int(match.group(2)), int(match.group(3))
            try:
                datetime(y, m, d)
                return f"{y:04d}-{m:02d}-{d:02d}"
            except ValueError:
                return None

        return None

    # ------------------------------------------------------------------
    # fix_file — file-level operation
    # ------------------------------------------------------------------
    def fix_file(self, file_path: str, dry_run: bool = False, backup: bool = True) -> FixResult:
        """
        Fix a skill card file. Handles parsing, fixing, and writing back.
        If backup=True and not dry_run, creates a .bak file.
        """
        result = FixResult(path=file_path, dry_run=dry_run)

        try:
            card = SkillCardParser.parse(file_path)
        except Exception as e:
            result.error = f"Parse error: {e}"
            return result

        # Fix in memory
        fixed = self.fix(card, dry_run=dry_run)

        if dry_run:
            result.success = True
            result.fixed_card = fixed.to_dict()
            return result

        # Backup
        if backup:
            bak_path = file_path + ".bak"
            try:
                shutil.copy2(file_path, bak_path)
                result.backup_path = bak_path
            except Exception as e:
                result.error = f"Backup failed: {e}"
                return result

        # Write back
        try:
            self._write_card(file_path, fixed.card)
        except Exception as e:
            result.error = f"Write failed: {e}"
            if result.backup_path and os.path.exists(result.backup_path):
                shutil.copy2(result.backup_path, file_path)
            return result

        result.success = True
        result.fixed_card = fixed.to_dict()
        return result

    def _write_card(self, file_path: str, card: Dict):
        """Write a card dict back to a markdown file with YAML frontmatter."""
        import yaml

        meta = card.get("metadata", {})
        body = card.get("body", "")

        frontmatter = yaml.dump(meta, allow_unicode=True, default_flow_style=False, sort_keys=False)
        content = f"---\n{frontmatter}---\n{body}"

        with open(file_path, "w", encoding="utf-8") as f:
            f.write(content)


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------

def main():
    import sys

    if len(sys.argv) < 2:
        print("Usage: python autofix.py <file_or_dir> [--dry-run] [--no-backup]")
        sys.exit(1)

    target = sys.argv[1]
    dry_run = "--dry-run" in sys.argv
    backup = "--no-backup" not in sys.argv

    fixer = AutoFixer()

    if os.path.isfile(target):
        print(f"{'[DRY RUN] ' if dry_run else ''}Fixing: {target}")
        result = fixer.fix_file(target, dry_run=dry_run, backup=backup)
        print(json.dumps(result.to_dict(), indent=2, ensure_ascii=False))
    elif os.path.isdir(target):
        from pathlib import Path
        for md_file in sorted(Path(target).rglob("*.md")):
            print(f"\n{'[DRY RUN] ' if dry_run else ''}Fixing: {md_file}")
            result = fixer.fix_file(str(md_file), dry_run=dry_run, backup=backup)
            print(json.dumps(result.to_dict(), indent=2, ensure_ascii=False))
    else:
        print(f"Target not found: {target}")
        sys.exit(1)


if __name__ == "__main__":
    main()
