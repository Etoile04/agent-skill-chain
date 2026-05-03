#!/usr/bin/env python3
"""Unit tests for the Skill Card JSON Schema validation.

Tests both valid and invalid skill cards against skill_card_schema.json
using Python 3 standard library only (json, jsonschema-like manual validation,
unittest).
"""

import json
import os
import re
import unittest
from typing import Any, Dict, List, Optional, Tuple

SCHEMA_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), "skill_card_schema.json")


def load_schema() -> dict:
    """Load the JSON schema from disk."""
    with open(SCHEMA_PATH, "r") as f:
        return json.load(f)


# ---------------------------------------------------------------------------
# Minimal JSON Schema validator (draft-07 subset used by our schema)
# ---------------------------------------------------------------------------

class SchemaValidator:
    """Validates JSON data against a subset of JSON Schema draft-07."""

    SEMVER_RE = re.compile(
        r"^(0|[1-9]\d*)\.(0|[1-9]\d*)\.(0|[1-9]\d*)"
        r"(?:-((?:0|[1-9]\d*|\d*[a-zA-Z-][0-9a-zA-Z-]*)(?:\.(?:0|[1-9]\d*|\d*[a-zA-Z-][0-9a-zA-Z-]*))*))?"
        r"(?:\+([0-9a-zA-Z-]+(?:\.[0-9a-zA-Z-]+)*))?$"
    )

    def __init__(self, schema: dict):
        self.schema = schema

    def validate(self, data: Any) -> List[str]:
        """Validate data against the schema. Returns list of error messages."""
        errors: List[str] = []
        self._validate_node(data, self.schema, "", errors)
        return errors

    def _validate_node(self, data: Any, schema: dict, path: str, errors: List[str]) -> None:
        """Recursively validate a node."""
        if schema.get("type") == "object":
            self._validate_object(data, schema, path, errors)
        elif schema.get("type") == "string":
            self._validate_string(data, schema, path, errors)
        elif schema.get("type") == "array":
            self._validate_array(data, schema, path, errors)
        elif schema.get("type") == "number":
            self._validate_number(data, schema, path, errors)
        elif schema.get("type") == "integer":
            if not isinstance(data, int):
                errors.append(f"{path}: expected integer, got {type(data).__name__}")
        elif schema.get("type") == "boolean":
            if not isinstance(data, bool):
                errors.append(f"{path}: expected boolean, got {type(data).__name__}")

    def _validate_object(self, data: Any, schema: dict, path: str, errors: List[str]) -> None:
        if not isinstance(data, dict):
            errors.append(f"{path or 'root'}: expected object, got {type(data).__name__}")
            return

        p = path or "root"

        # Check required fields
        required = schema.get("required", [])
        for field in required:
            if field not in data:
                errors.append(f"{p}.{field}: required field missing")

        # Check additionalProperties
        if schema.get("additionalProperties") is False:
            allowed = set(schema.get("properties", {}).keys())
            for key in data:
                if key not in allowed:
                    errors.append(f"{p}.{key}: additional property not allowed")

        # Validate each property against its schema
        properties = schema.get("properties", {})
        for key, prop_schema in properties.items():
            if key in data:
                self._validate_node(data[key], prop_schema, f"{p}.{key}", errors)

    def _validate_string(self, data: Any, schema: dict, path: str, errors: List[str]) -> None:
        if not isinstance(data, str):
            errors.append(f"{path}: expected string, got {type(data).__name__}")
            return

        min_len = schema.get("minLength")
        if min_len is not None and len(data) < min_len:
            errors.append(f"{path}: string length {len(data)} < minLength {min_len}")

        max_len = schema.get("maxLength")
        if max_len is not None and len(data) > max_len:
            errors.append(f"{path}: string length {len(data)} > maxLength {max_len}")

        enum_val = schema.get("enum")
        if enum_val is not None and data not in enum_val:
            errors.append(f"{path}: value '{data}' not in enum {enum_val}")

        pattern = schema.get("pattern")
        if pattern is not None and not re.match(pattern, data):
            errors.append(f"{path}: value '{data}' does not match pattern")

        fmt = schema.get("format")
        if fmt == "date":
            # Validate YYYY-MM-DD
            try:
                from datetime import date as date_type
                parts = data.split("-")
                if len(parts) != 3:
                    raise ValueError
                date_type(int(parts[0]), int(parts[1]), int(parts[2]))
            except (ValueError, TypeError):
                errors.append(f"{path}: '{data}' is not a valid date (YYYY-MM-DD)")

    def _validate_array(self, data: Any, schema: dict, path: str, errors: List[str]) -> None:
        if not isinstance(data, list):
            errors.append(f"{path}: expected array, got {type(data).__name__}")
            return

        min_items = schema.get("minItems")
        if min_items is not None and len(data) < min_items:
            errors.append(f"{path}: array length {len(data)} < minItems {min_items}")

        items_schema = schema.get("items")
        if items_schema is not None:
            for i, item in enumerate(data):
                self._validate_node(item, items_schema, f"{path}[{i}]", errors)

    def _validate_number(self, data: Any, schema: dict, path: str, errors: List[str]) -> None:
        if not isinstance(data, (int, float)):
            errors.append(f"{path}: expected number, got {type(data).__name__}")


# ---------------------------------------------------------------------------
# Test data
# ---------------------------------------------------------------------------

def _make_valid_card(**overrides) -> dict:
    """Create a minimal valid skill card, with optional overrides."""
    card = {
        "name": "Test Skill Card",
        "category": "pattern",
        "description": "A test skill card for validation testing purposes.",
        "when_to_use": ["When encountering test scenarios", "During validation"],
        "common_failures": ["Failure pattern A", "Failure pattern B"],
    }
    card.update(overrides)
    return card


VALID_FULL_CARD = {
    "name": "A2A Gateway Complex Task Timeout Pattern",
    "category": "pattern",
    "description": "Pattern for handling A2A Gateway timeouts when dispatching complex tasks to remote agents.",
    "when_to_use": [
        "When dispatching tasks through A2A Gateway",
        "When tasks take longer than 30 seconds",
        "When A2A dispatch returns timeout errors",
    ],
    "common_failures": [
        "A2A complex task stable timeout on main agent route",
        "Sync dispatch entry timeout",
        "Repeated attempts at homogeneous solutions waste time",
    ],
    "version": "1.0.0",
    "tags": ["a2a", "timeout", "agent-communication", "async"],
    "related_cards": ["a2a-gateway-setup", "error-diagnosis-depth"],
    "created_at": "2026-05-02",
    "updated_at": "2026-05-03",
    "priority": "high",
}

VALID_WORKFLOW_CARD = {
    "name": "A2A Gateway Setup Workflow",
    "category": "workflow",
    "description": "Step-by-step workflow for installing and debugging the A2A Gateway plugin for inter-agent communication.",
    "when_to_use": [
        "Installing a new version of A2A Gateway",
        "Debugging agent communication issues",
        "Running regression tests after Gateway upgrade",
    ],
    "common_failures": [
        "A2A dispatch timeout due to agent session mutex",
        "npm install blocked by security policy",
        "Residual tasks causing Gateway state anomalies",
    ],
    "priority": "medium",
}

VALID_DOMAIN_CARD = {
    "name": "Knowledge Base Sync",
    "category": "domain",
    "description": "Domain knowledge for building local wikis and synchronizing them with Feishu knowledge spaces.",
    "when_to_use": [
        "After reading a new paper",
        "When syncing local knowledge to Feishu",
        "When knowledge base structure changes",
    ],
    "common_failures": [
        "Feishu API folder locked error on concurrent writes",
        "Incremental sync fails to detect file changes",
        "Chinese filenames causing encoding errors",
    ],
    "version": "2.3.1-alpha",
    "tags": ["wiki", "feishu", "sync"],
}


class TestSchemaValid(unittest.TestCase):
    """Test that valid skill cards pass validation."""

    def setUp(self):
        self.schema = load_schema()
        self.validator = SchemaValidator(self.schema)

    def test_minimal_valid_card(self):
        """Minimal card with only required fields should pass."""
        card = _make_valid_card()
        errors = self.validator.validate(card)
        self.assertEqual(errors, [], f"Expected no errors, got: {errors}")

    def test_full_valid_card_pattern(self):
        """Full card with all optional fields, category=pattern."""
        errors = self.validator.validate(VALID_FULL_CARD)
        self.assertEqual(errors, [], f"Expected no errors, got: {errors}")

    def test_full_valid_card_workflow(self):
        """Full card with some optional fields, category=workflow."""
        errors = self.validator.validate(VALID_WORKFLOW_CARD)
        self.assertEqual(errors, [], f"Expected no errors, got: {errors}")

    def test_full_valid_card_domain(self):
        """Full card with some optional fields, category=domain."""
        errors = self.validator.validate(VALID_DOMAIN_CARD)
        self.assertEqual(errors, [], f"Expected no errors, got: {errors}")

    def test_valid_with_all_categories(self):
        """Each valid category enum value should pass."""
        for cat in ["pattern", "workflow", "domain"]:
            card = _make_valid_card(category=cat)
            errors = self.validator.validate(card)
            self.assertEqual(errors, [], f"Category '{cat}' should be valid, got: {errors}")

    def test_valid_with_all_priorities(self):
        """Each valid priority enum value should pass."""
        for pri in ["high", "medium", "low"]:
            card = _make_valid_card(priority=pri)
            errors = self.validator.validate(card)
            self.assertEqual(errors, [], f"Priority '{pri}' should be valid, got: {errors}")

    def test_valid_with_semver_versions(self):
        """Various valid semver strings."""
        versions = ["1.0.0", "0.1.0", "2.3.1-alpha", "1.0.0-beta.1", "3.2.1+build.123"]
        for v in versions:
            card = _make_valid_card(version=v)
            errors = self.validator.validate(card)
            self.assertEqual(errors, [], f"Version '{v}' should be valid, got: {errors}")

    def test_valid_without_optional_fields(self):
        """Card without any optional fields should pass."""
        card = _make_valid_card()
        # Ensure no optional fields are present
        for opt in ["version", "tags", "related_cards", "created_at", "updated_at", "priority"]:
            self.assertNotIn(opt, card)
        errors = self.validator.validate(card)
        self.assertEqual(errors, [], f"Expected no errors, got: {errors}")

    def test_valid_boundary_name_min_length(self):
        """Name with exactly 3 characters (minLength boundary)."""
        card = _make_valid_card(name="abc")
        errors = self.validator.validate(card)
        self.assertEqual(errors, [], f"Expected no errors, got: {errors}")

    def test_valid_boundary_name_max_length(self):
        """Name with exactly 100 characters (maxLength boundary)."""
        card = _make_valid_card(name="a" * 100)
        errors = self.validator.validate(card)
        self.assertEqual(errors, [], f"Expected no errors, got: {errors}")

    def test_valid_boundary_description_min_length(self):
        """Description with exactly 10 characters (minLength boundary)."""
        card = _make_valid_card(description="1234567890")
        errors = self.validator.validate(card)
        self.assertEqual(errors, [], f"Expected no errors, got: {errors}")

    def test_valid_boundary_description_max_length(self):
        """Description with exactly 500 characters (maxLength boundary)."""
        card = _make_valid_card(description="x" * 500)
        errors = self.validator.validate(card)
        self.assertEqual(errors, [], f"Expected no errors, got: {errors}")

    def test_valid_empty_tags_array(self):
        """Empty tags array should be valid (no minItems constraint on tags)."""
        card = _make_valid_card(tags=[])
        errors = self.validator.validate(card)
        self.assertEqual(errors, [], f"Expected no errors, got: {errors}")


class TestSchemaInvalid(unittest.TestCase):
    """Test that invalid skill cards are rejected."""

    def setUp(self):
        self.schema = load_schema()
        self.validator = SchemaValidator(self.schema)

    # --- Missing required fields ---

    def test_missing_name(self):
        card = _make_valid_card()
        del card["name"]
        errors = self.validator.validate(card)
        self.assertTrue(any("name" in e and "required" in e for e in errors),
                        f"Expected required error for 'name', got: {errors}")

    def test_missing_category(self):
        card = _make_valid_card()
        del card["category"]
        errors = self.validator.validate(card)
        self.assertTrue(any("category" in e and "required" in e for e in errors),
                        f"Expected required error for 'category', got: {errors}")

    def test_missing_description(self):
        card = _make_valid_card()
        del card["description"]
        errors = self.validator.validate(card)
        self.assertTrue(any("description" in e and "required" in e for e in errors),
                        f"Expected required error for 'description', got: {errors}")

    def test_missing_when_to_use(self):
        card = _make_valid_card()
        del card["when_to_use"]
        errors = self.validator.validate(card)
        self.assertTrue(any("when_to_use" in e and "required" in e for e in errors),
                        f"Expected required error for 'when_to_use', got: {errors}")

    def test_missing_common_failures(self):
        card = _make_valid_card()
        del card["common_failures"]
        errors = self.validator.validate(card)
        self.assertTrue(any("common_failures" in e and "required" in e for e in errors),
                        f"Expected required error for 'common_failures', got: {errors}")

    def test_empty_object(self):
        """Completely empty object should fail all required fields."""
        errors = self.validator.validate({})
        required_fields = ["name", "category", "description", "when_to_use", "common_failures"]
        for field in required_fields:
            self.assertTrue(any(field in e and "required" in e for e in errors),
                            f"Expected required error for '{field}', got: {errors}")

    # --- Type errors ---

    def test_name_is_number(self):
        card = _make_valid_card(name=42)
        errors = self.validator.validate(card)
        self.assertTrue(any("name" in e and "string" in e for e in errors),
                        f"Expected type error for 'name', got: {errors}")

    def test_category_is_number(self):
        card = _make_valid_card(category=123)
        errors = self.validator.validate(card)
        self.assertTrue(any("category" in e and "string" in e for e in errors),
                        f"Expected type error for 'category', got: {errors}")

    def test_description_is_array(self):
        card = _make_valid_card(description=["not", "a", "string"])
        errors = self.validator.validate(card)
        self.assertTrue(any("description" in e and "string" in e for e in errors),
                        f"Expected type error for 'description', got: {errors}")

    def test_when_to_use_is_string(self):
        card = _make_valid_card(when_to_use="single string not array")
        errors = self.validator.validate(card)
        self.assertTrue(any("when_to_use" in e and "array" in e for e in errors),
                        f"Expected type error for 'when_to_use', got: {errors}")

    def test_common_failures_is_object(self):
        card = _make_valid_card(common_failures={"key": "value"})
        errors = self.validator.validate(card)
        self.assertTrue(any("common_failures" in e and "array" in e for e in errors),
                        f"Expected type error for 'common_failures', got: {errors}")

    def test_tags_is_string(self):
        card = _make_valid_card(tags="not an array")
        errors = self.validator.validate(card)
        self.assertTrue(any("tags" in e and "array" in e for e in errors),
                        f"Expected type error for 'tags', got: {errors}")

    def test_root_is_array(self):
        """Root should be an object, not an array."""
        errors = self.validator.validate([{"name": "test"}])
        self.assertTrue(any("object" in e for e in errors),
                        f"Expected object type error at root, got: {errors}")

    # --- Enum violations ---

    def test_invalid_category_enum(self):
        card = _make_valid_card(category="infrastructure")
        errors = self.validator.validate(card)
        self.assertTrue(any("category" in e and "enum" in e for e in errors),
                        f"Expected enum error for 'category', got: {errors}")

    def test_invalid_category_patterns_lowercase(self):
        """'patterns' (plural) is not valid — must be singular 'pattern'."""
        card = _make_valid_card(category="patterns")
        errors = self.validator.validate(card)
        self.assertTrue(any("category" in e and "enum" in e for e in errors),
                        f"Expected enum error for 'category', got: {errors}")

    def test_invalid_priority_enum(self):
        card = _make_valid_card(priority="critical")
        errors = self.validator.validate(card)
        self.assertTrue(any("priority" in e and "enum" in e for e in errors),
                        f"Expected enum error for 'priority', got: {errors}")

    def test_invalid_priority_case(self):
        """'High' (capitalized) is not valid — must be lowercase."""
        card = _make_valid_card(priority="High")
        errors = self.validator.validate(card)
        self.assertTrue(any("priority" in e and "enum" in e for e in errors),
                        f"Expected enum error for 'priority', got: {errors}")

    # --- Length violations ---

    def test_name_too_short(self):
        card = _make_valid_card(name="ab")
        errors = self.validator.validate(card)
        self.assertTrue(any("name" in e and "minLength" in e for e in errors),
                        f"Expected minLength error for 'name', got: {errors}")

    def test_name_too_long(self):
        card = _make_valid_card(name="a" * 101)
        errors = self.validator.validate(card)
        self.assertTrue(any("name" in e and "maxLength" in e for e in errors),
                        f"Expected maxLength error for 'name', got: {errors}")

    def test_name_empty_string(self):
        card = _make_valid_card(name="")
        errors = self.validator.validate(card)
        self.assertTrue(any("name" in e and "minLength" in e for e in errors),
                        f"Expected minLength error for 'name', got: {errors}")

    def test_description_too_short(self):
        card = _make_valid_card(description="short")
        errors = self.validator.validate(card)
        self.assertTrue(any("description" in e and "minLength" in e for e in errors),
                        f"Expected minLength error for 'description', got: {errors}")

    def test_description_too_long(self):
        card = _make_valid_card(description="x" * 501)
        errors = self.validator.validate(card)
        self.assertTrue(any("description" in e and "maxLength" in e for e in errors),
                        f"Expected maxLength error for 'description', got: {errors}")

    # --- Array item constraints ---

    def test_when_to_use_empty_array(self):
        """when_to_use has minItems=1, empty array should fail."""
        card = _make_valid_card(when_to_use=[])
        errors = self.validator.validate(card)
        self.assertTrue(any("when_to_use" in e and "minItems" in e for e in errors),
                        f"Expected minItems error for 'when_to_use', got: {errors}")

    def test_common_failures_empty_array(self):
        """common_failures has minItems=1, empty array should fail."""
        card = _make_valid_card(common_failures=[])
        errors = self.validator.validate(card)
        self.assertTrue(any("common_failures" in e and "minItems" in e for e in errors),
                        f"Expected minItems error for 'common_failures', got: {errors}")

    def test_when_to_use_with_empty_string_item(self):
        """Array items must have minLength=1, empty string should fail."""
        card = _make_valid_card(when_to_use=["valid string", ""])
        errors = self.validator.validate(card)
        self.assertTrue(any("when_to_use" in e and "minLength" in e for e in errors),
                        f"Expected minLength error for empty array item, got: {errors}")

    # --- Additional properties ---

    def test_additional_property_rejected(self):
        """Fields not in the schema should be rejected (additionalProperties: false)."""
        card = _make_valid_card(unknown_field="some value")
        errors = self.validator.validate(card)
        self.assertTrue(any("unknown_field" in e and "additional" in e.lower() for e in errors),
                        f"Expected additional property error, got: {errors}")

    def test_multiple_additional_properties(self):
        """Multiple unknown fields should all be reported."""
        card = _make_valid_card(foo="bar", baz=42)
        errors = self.validator.validate(card)
        extra = [e for e in errors if "additional" in e.lower()]
        self.assertEqual(len(extra), 2, f"Expected 2 additional property errors, got: {errors}")

    # --- Invalid semver ---

    def test_invalid_version_not_semver(self):
        """Version must match semver pattern."""
        card = _make_valid_card(version="v1.0")
        errors = self.validator.validate(card)
        self.assertTrue(any("version" in e and "pattern" in e for e in errors),
                        f"Expected pattern error for 'version', got: {errors}")

    def test_invalid_version_plain_text(self):
        card = _make_valid_card(version="latest")
        errors = self.validator.validate(card)
        self.assertTrue(any("version" in e and "pattern" in e for e in errors),
                        f"Expected pattern error for 'version', got: {errors}")

    # --- Invalid date format ---

    def test_invalid_created_at_format(self):
        card = _make_valid_card(created_at="2026/05/02")
        errors = self.validator.validate(card)
        self.assertTrue(any("created_at" in e and "date" in e.lower() for e in errors),
                        f"Expected date format error for 'created_at', got: {errors}")

    def test_invalid_updated_at_text(self):
        card = _make_valid_card(updated_at="yesterday")
        errors = self.validator.validate(card)
        self.assertTrue(any("updated_at" in e and "date" in e.lower() for e in errors),
                        f"Expected date format error for 'updated_at', got: {errors}")

    # --- Combination errors ---

    def test_missing_required_and_invalid_enum(self):
        """Multiple errors should all be reported."""
        card = {
            "category": "invalid_cat",
            "description": "A valid description here",
            "when_to_use": ["scenario one"],
            "common_failures": ["failure one"],
            # name is missing
        }
        errors = self.validator.validate(card)
        has_missing = any("name" in e and "required" in e for e in errors)
        has_enum = any("category" in e and "enum" in e for e in errors)
        self.assertTrue(has_missing, f"Expected missing 'name' error, got: {errors}")
        self.assertTrue(has_enum, f"Expected enum error for 'category', got: {errors}")


if __name__ == "__main__":
    unittest.main()
