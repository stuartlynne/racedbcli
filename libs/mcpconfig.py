#!/usr/bin/env python3

import json
import os


DEFAULT_CONFIG = "~/.mcp.json"


def load_mcp_host(name, config_file=None):
    path = os.path.expanduser(config_file or os.getenv("RACEDB_MCP_CONFIG", DEFAULT_CONFIG))
    try:
        with open(path, "r", encoding="utf-8") as f:
            config = json.load(f)
    except FileNotFoundError as e:
        raise RuntimeError(f"MCP host config not found: {path}") from e
    except json.JSONDecodeError as e:
        raise RuntimeError(f"MCP host config has invalid JSON: {path}: {e}") from e

    entry = config.get(name)
    if not isinstance(entry, dict):
        available = ", ".join(sorted(config.keys()))
        raise RuntimeError(f"MCP host [{name}] not found in {path}. Available: {available}")

    racedb_url = entry.get("racedb_url")
    mcp_url = entry.get("mcp_url")
    if not racedb_url:
        raise RuntimeError(f"MCP host [{name}] missing racedb_url in {path}")

    return {
        "name": name,
        "racedb_url": racedb_url,
        "mcp_url": mcp_url,
    }

