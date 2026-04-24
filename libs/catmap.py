#!/usr/bin/env python3

import json
import os
import sys
from typing import Any, Dict, List, Optional, Tuple
import re
import ast

   
TT_speeds = {
    ('Cat 1',  ['M', 46], ['F', 44],        
    ('Cat 2',  ['M', 45], ['F', 43],        
    ('Cat 3',  ['M', 43], ['F', 41],        
    ('Cat 4',  ['M', 42], ['F', 40],        
    ('Cat 5',  ['M', 41], ['F', 39],        
}


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
        self.allowed: List[List[Any]] = []
        self._load()

    @property
    def json_path(self) -> str:
        return os.path.join(self.base_dir, f"{self.format_name}.json")

    def json_load(self, path: str) -> Any:
        """Load a JSON file allowing shell-style comments starting with '#'.

        Strips trailing comments from each line, then parses as a tolerant
        Python literal (via ast.literal_eval). Falls back to json.loads.
        Also converts tuples to lists to be JSON-compatible in-memory.
        """
        try:
            with open(path, "r", encoding="utf-8") as f:
                lines: List[str] = []
                for line in f:
                    # Remove comments starting with '#'
                    line = re.sub(r"#.*$", "", line)
                    lines.append(line)
                content = "".join(lines).strip()

                def to_jsonable(x: Any) -> Any:
                    if isinstance(x, dict):
                        return {k: to_jsonable(v) for k, v in x.items()}
                    if isinstance(x, (list, tuple)):
                        return [to_jsonable(v) for v in x]
                    return x

                # First try Python literal eval (handles single quotes, tuples, None, trailing commas)
                try:
                    data = ast.literal_eval(content)
                    return to_jsonable(data)
                except Exception:
                    pass

                # Fallback to strict JSON
                return json.loads(content)
        except FileNotFoundError:
            print(f"CatMap: file not found {path}", file=sys.stdout)
        except json.JSONDecodeError as e:
            print(f"CatMap: invalid JSON in {path}: {e}", file=sys.stdout)
        except Exception as e:
            print(f"CatMap: failed to parse {path}: {e}", file=sys.stdout)
        return None

    def _load(self) -> None:
        path = self.json_path
        data = self.json_load(path)
        if isinstance(data, dict):
            self.map = data
        else:
            self.map = {}

        # Load allowed categories rules from optional '<format>-allowed.json'
        allowed_path = os.path.join(self.base_dir, f"{self.format_name}-allowed.json")
        allowed_data = self.json_load(allowed_path)
        if isinstance(allowed_data, list):
            self.allowed = allowed_data
        else:
            self.allowed = []
        print(f"CatMap: loaded {len(self.map)} mappings and {len(self.allowed)} allowed rules from {path} and {allowed_path}", file=sys.stdout)
        # print(f"CatMap: {allowed_data}", file=sys.stdout)
        for t in self.allowed:
            print(f"  allowed rule: {t}", file=sys.stdout)

    def lookup_label(self, label: str) -> Optional[List[Any]]:
        """Return the mapping entry for the exact label, or None if not found."""
        return self.map.get(label)

    def get_map(self) -> Dict[str, List[Any]]:
        return self.map

    def get_event_category(
        self,
        license_categories: Optional[Dict[str, List[Optional[str]]]],
        gender: Optional[str],
        age: Optional[int],
        event_categories: Optional[List[List[Any]]] = None,
        discipline: Optional[str] = None,
    ) -> Tuple[List[str], Dict[str, List[Optional[str]]]]:
        """Compute allowed event categories from license, gender, and age.

        - license_categories: mapping like { 'Cyclocross': ['Cat 3', 'Elite'], 'Road': [...] }
        - gender: 'M', 'F', or None
        - age: int or None
        - event_categories: override list; otherwise uses loaded 'allowed' rules.

        Returns (allowed_categories, {selected_type: licenses}).
        """
        rules = event_categories if event_categories is not None else self.allowed

        # Select a license type to consider
        selected_type = None
        licenses: List[Optional[str]] = [None]
        if isinstance(license_categories, dict) and license_categories:
            #if 'Cyclocross' in license_categories and license_categories['Cyclocross']:
            #    selected_type = 'Cyclocross'
            #elif 'Road' in license_categories and license_categories['Road']:
            #    selected_type = 'Road'
            if discipline in license_categories:
                selected_type = discipline
            else:
                # pick any available key
                selected_type = next(iter(license_categories.keys()))
            licenses = license_categories.get(selected_type) or [None]

        print(f"CatMap: computing event category for licenses={licenses}", file=sys.stderr)

        gnorm = None
        if isinstance(gender, str):
            gnorm = gender.strip().upper()
            if gnorm and gnorm[0] in ('M', 'F'):
                gnorm = gnorm[0]
            elif gname == "Men":
                gnorm = 'M'
            elif gname == "Women":
                gnorm = 'F'
            else:
                gnorm = None

        print(f"CatMap: normalized gender={gnorm}, age={age}, selected_type={selected_type}", file=sys.stderr)
        allowed_categories: List[str] = []

        def log(i: int, j: int, lic: str, rule: List[Any], msg: str) -> None:
            if True:
                req_license, req_gender, (min_age, max_age), cats = rule[0], rule[1], rule[2], rule[3]
                print(f"CatMap[{i}:{j}] lic={lic} req_license={req_license}, req_gender={req_gender}, min_age={min_age}, max_age={max_age}, cats={cats} {msg}", file=sys.stderr)

        if licenses is not None and len(licenses) != 0:
            for i, lic in enumerate(licenses or [None]):
                if lic is None:
                    pass
                for j, rule in enumerate(rules):
                    if not isinstance(rule, list) or len(rule) < 4:
                        continue
                    req_license, req_gender, (min_age, max_age), cats = rule[0], rule[1], rule[2], rule[3]

                    # Gender must match if specified
                    if req_gender and gnorm and req_gender != gnorm:
                        log(i, j, lic, rule, "gender mismatch")
                        continue

                    # License must match if specified and not ANY
                    if False:
                        if req_license == 'ANY':
                            pass
                        elif req_license and lic and req_license != lic:
                            log(i, j, lic, rule, f"license mismatch (required {req_license}, got {lic})")
                            continue
                        elif req_license and not lic:
                            log(i, j, lic, rule, f"license mismatch (license required but not provided)")
                            continue
                    if True:
                        if lic and cats and lic not in cats:
                            log(i, j, lic, rule, f"license {lic} not in allowed categories {cats}")
                            continue

                    # Age bounds
                    if age is not None and min_age is not None and int(age) < int(min_age):
                        log(i, j, lic, rule, f"age {age} below min {min_age}")
                        continue
                    if age is not None and max_age is not None and int(age) > int(max_age):
                        log(i, j, lic, rule, f"age {age} above max {max_age}")
                        continue

                    # Add categories uniquely
                    if False:
                        if cats:
                            log(i, j, lic, rule, "rule matches, adding categories " + ", ".join(cats))
                            for c in cats:
                                if c not in allowed_categories:
                                    allowed_categories.append(c)
                    if True and req_license:
                        allowed_categories.extend([req_license]) 

        return allowed_categories, ({selected_type: licenses} if selected_type else {'': licenses})


if __name__ == "__main__":
    fmt = sys.argv[1] if len(sys.argv) > 1 else "lmcx2018"
    cm = CatMap(fmt)
    print(f"Loaded {len(cm.get_map())} mappings for {fmt}")
    print(f"Loaded {len(cm.allowed)} allowed rules for {fmt}")
    for test in ["Masters Men 40-45", "Masters Beer League"]:
        print(test, "->", cm.lookup_label(test))
