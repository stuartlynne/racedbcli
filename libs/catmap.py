#!/usr/bin/env python3

import json
import os
import sys
from typing import Any, Dict, List, Optional


def _norm_label(label: str) -> str:
    # Keep a simple normalizer available if we need it later
    if label is None:
        return ""
    return " ".join(str(label).split())


class CatMap:
    """Load per-format organizer label mapping from catmap/<format>.json.

    New format: a JSON object mapping organizer labels to an array
    [normalized_category, gender], e.g.:

      {
        "Elite Men Cat 1/2/3": ["Elite Cat 1/2/3", "Men"],
        "Novice Women": ["Novice", "Women"]
      }
    """

    def __init__(self, format_name: str, base_dir: Optional[str] = None) -> None:
        self.format_name = format_name
        self.base_dir = base_dir or os.path.join(os.path.dirname(os.path.dirname(__file__)), "catmap")
        self.map: Dict[str, List[Any]] = {}
        self._load()

    @property
    def json_path(self) -> str:
        return os.path.join(self.base_dir, f"{self.format_name}.json")

    def _load(self) -> None:
        path = self.json_path
        try:
            with open(path, "r", encoding="utf-8") as f:
                data = json.load(f)
            if isinstance(data, dict):
                self.map = data
            else:
                print(f"CatMap: expected dict at {path}; got {type(data).__name__}", file=sys.stderr)
                self.map = {}
        except FileNotFoundError:
            print(f"CatMap: no mapping file found at {path}", file=sys.stderr)
            self.map = {}
        except json.JSONDecodeError as e:
            print(f"CatMap: invalid JSON in {path}: {e}", file=sys.stderr)
            self.map = {}

    def lookup_label(self, label: str) -> Optional[List[Any]]:
        """Return the mapping entry for the exact label, or None if not found."""
        return self.map.get(label)

    def get_map(self) -> Dict[str, List[Any]]:
        return self.map


if __name__ == "__main__":
    fmt = sys.argv[1] if len(sys.argv) > 1 else "lmcx2018"
    cm = CatMap(fmt)
    print(f"Loaded {len(cm.get_map())} mappings for {fmt}")
    for test in ["Masters Men 40-45", "Masters Beer League"]:
        print(test, "->", cm.lookup_label(test))
