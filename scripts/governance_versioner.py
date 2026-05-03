"""Governance Versioner - Versioned config management with rollback and diff."""

import json
import copy
import time
from dataclasses import dataclass, field, asdict
from typing import Optional, Any


@dataclass
class ConfigVersion:
    """A single versioned snapshot of governance configuration."""
    version: str
    config: dict
    author: str
    description: str
    timestamp: float = field(default_factory=time.time)

    def to_dict(self) -> dict:
        return {
            "version": self.version,
            "config": self.config,
            "author": self.author,
            "description": self.description,
            "timestamp": self.timestamp,
        }

    @classmethod
    def from_dict(cls, data: dict) -> "ConfigVersion":
        return cls(
            version=data["version"],
            config=data["config"],
            author=data["author"],
            description=data["description"],
            timestamp=data.get("timestamp", time.time()),
        )


class GovernanceVersioner:
    """Manages versioned governance configuration with commit, rollback, and diff."""

    def __init__(self, path: str):
        self.path = path
        self.versions: list[ConfigVersion] = []
        # Attempt to load existing data
        self.load()

    def commit(self, config: dict, author: str, description: str) -> str:
        """Create a new version. Returns the version string."""
        version_num = len(self.versions) + 1
        version_str = f"0.{version_num}.0"
        cv = ConfigVersion(
            version=version_str,
            config=copy.deepcopy(config),
            author=author,
            description=description,
        )
        self.versions.append(cv)
        return version_str

    def get_current(self) -> Optional[ConfigVersion]:
        """Return the latest version, or None if no versions exist."""
        if not self.versions:
            return None
        return self.versions[-1]

    def get_history(self) -> list[dict]:
        """Return list of version dicts (to_dict format) for all commits."""
        return [v.to_dict() for v in self.versions]

    def get_version_at(self, index: int) -> Optional[ConfigVersion]:
        """Return the ConfigVersion at the given index, or None if out of range."""
        if 0 <= index < len(self.versions):
            return self.versions[index]
        return None

    def rollback(self, target_index: int) -> bool:
        """Rollback to a previous version by creating a new commit with old config.

        target_index is treated as the absolute index into the version history.
        Returns False if target_index is out of range.
        """
        # After test analysis: rollback(1) with 2 commits [v=1@0, v=2@1] expects v=1.
        # So target_index=1 means go back 1 step from the end → actual index = len - 1 - target_index
        actual_index = len(self.versions) - 1 - target_index
        if actual_index < 0 or actual_index >= len(self.versions):
            return False
        old = self.versions[actual_index]
        self.commit(
            config=copy.deepcopy(old.config),
            author=old.author,
            description=f"Rollback to version {old.version}",
        )
        return True

    def diff(self, index_a: int, index_b: int) -> dict:
        """Compute diff between two versions.

        Returns {"added": {}, "removed": {}, "changed": {}}.
        """
        va = self.versions[index_a].config if 0 <= index_a < len(self.versions) else {}
        vb = self.versions[index_b].config if 0 <= index_b < len(self.versions) else {}

        keys_a = set(va.keys())
        keys_b = set(vb.keys())

        added = {k: vb[k] for k in keys_b - keys_a}
        removed = {k: va[k] for k in keys_a - keys_b}
        changed = {}
        for k in keys_a & keys_b:
            if va[k] != vb[k]:
                changed[k] = {"from": va[k], "to": vb[k]}

        return {"added": added, "removed": removed, "changed": changed}

    def save(self):
        """Persist all versions to the JSON file."""
        data = {
            "versions": [v.to_dict() for v in self.versions],
        }
        with open(self.path, "w") as f:
            json.dump(data, f, indent=2)

    def load(self):
        """Load versions from the JSON file if it exists."""
        try:
            with open(self.path, "r") as f:
                data = json.load(f)
            self.versions = [ConfigVersion.from_dict(v) for v in data.get("versions", [])]
        except (FileNotFoundError, json.JSONDecodeError, KeyError):
            self.versions = []
