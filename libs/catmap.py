#!/usr/bin/env python3

import json
import os
import sys
from typing import Any, Dict, List, Optional, Tuple


def _norm_label(label: str) -> str:
    """Normalize organizer-provided category labels for matching.

    - Collapse repeated whitespace
    - Strip surrounding quotes
    """
    if label is None:
        return ""
    # Remove quotes and collapse whitespace
    cleaned = " ".join(str(label).replace('"', "").split())
    return cleaned


class CatMap:
    """Load per-format category mapping and lookups from catmap/<format>.json.

    Expected JSON structure (example):
    {
      "event_categories": [
        ["Cat 5", null, [null, null], ["Novice"]],
        ["Elite", "M", [19, null], ["Elite"]]
      ],
      "label_aliases": [
        ["Masters Men 40-45", "M", "Master A"],
        ["Masters Beer League", null, "Master A"]
      ]
    }
    """

    def __init__(self, format_name: str, base_dir: Optional[str] = None) -> None:
        self.format_name = format_name
        self.base_dir = base_dir or os.path.join(os.path.dirname(os.path.dirname(__file__)), "catmap")
        self.event_categories: List[List[Any]] = []
        self.label_aliases: List[List[Any]] = []
        self._load()

    @property
    def json_path(self) -> str:
        return os.path.join(self.base_dir, f"{self.format_name}.json")

    def _load(self) -> None:
        path = self.json_path
        try:
            with open(path, "r", encoding="utf-8") as f:
                data: Dict[str, Any] = json.load(f)
        except FileNotFoundError:
            print(f"CatMap: no mapping file found at {path}", file=sys.stderr)
            data = {}
        except json.JSONDecodeError as e:
            print(f"CatMap: invalid JSON in {path}: {e}", file=sys.stderr)
            data = {}

        self.event_categories = data.get("event_categories", [])
        self.label_aliases = data.get("label_aliases", [])

    def lookup_label(self, label: str, gender: Optional[str] = None) -> Optional[Tuple[Any, ...]]:
        """Return the first matching alias tuple for an organizer label.

        Match rules:
        - First element (alias label) must match normalized input label (case-sensitive as stored; adjust if needed).
        - If alias specifies a gender (M/F), and input gender is provided, they must match.

        Returns the matching tuple as a Python tuple, or None if not found.
        """
        target = _norm_label(label)
        for entry in self.label_aliases:
            if not entry:
                continue
            alias_label = _norm_label(entry[0])
            alias_gender = entry[1] if len(entry) > 1 else None
            if alias_label != target:
                continue
            if alias_gender and gender and alias_gender != gender:
                continue
            return tuple(entry)
        return None

    def get_event_categories(self) -> List[List[Any]]:
        """Return the raw event_categories definition for this format."""
        return self.event_categories


if __name__ == "__main__":
    # Quick manual test:
    fmt = sys.argv[1] if len(sys.argv) > 1 else "lmcx2018"
    cm = CatMap(fmt)
    print(f"Loaded {len(cm.get_event_categories())} event rules for {fmt}")
    for test in [("Masters Men 40-45", "M"), ("Masters Beer League", None)]:
        label, gen = test
        print(label, gen, "->", cm.lookup_label(label, gen))

