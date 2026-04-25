#!/usr/bin/env python3
from __future__ import annotations

import argparse
import ast
import json
import sys
from copy import deepcopy
from pathlib import Path
from typing import Any

ROOT_DIR = Path(__file__).resolve().parents[2]
BACKEND_DIR = ROOT_DIR / "backend"
VERTICALS_SOURCE = BACKEND_DIR / "app" / "verticals" / "implementation.py"
VERTICAL_10X_SOURCE = BACKEND_DIR / "app" / "vertical_10x" / "implementation.py"
PORTFOLIO_UPDATES = BACKEND_DIR / "app" / "data" / "vertical_portfolio_updates.json"


def _deep_merge(base: Any, updates: Any) -> Any:
    if isinstance(base, dict) and isinstance(updates, dict):
        merged = deepcopy(base)
        for key, value in updates.items():
            merged[key] = _deep_merge(merged[key], value) if key in merged else deepcopy(value)
        return merged
    return deepcopy(updates)


def _literal_assignment(path: Path, name: str) -> Any:
    tree = ast.parse(path.read_text(encoding="utf-8"), filename=str(path))
    for node in tree.body:
        if isinstance(node, ast.Assign):
            for target in node.targets:
                if isinstance(target, ast.Name) and target.id == name:
                    return ast.literal_eval(node.value)
        if isinstance(node, ast.AnnAssign) and isinstance(node.target, ast.Name) and node.target.id == name:
            return ast.literal_eval(node.value)
    raise RuntimeError(f"Could not find literal assignment {name} in {path}")


def _fallback_profiles() -> list[dict[str, Any]]:
    profiles = _literal_assignment(VERTICALS_SOURCE, "_VERTICALS")
    if PORTFOLIO_UPDATES.exists():
        payload = json.loads(PORTFOLIO_UPDATES.read_text(encoding="utf-8"))
        updates = {str(item.get("id")): item for item in payload.get("verticals", []) if item.get("id")}
        merged: list[dict[str, Any]] = []
        seen: set[str] = set()
        for item in profiles:
            key = str(item.get("id") or "")
            merged.append(_deep_merge(item, updates[key]) if key in updates else deepcopy(item))
            seen.add(key)
        for key, patch in updates.items():
            if key not in seen:
                merged.append(deepcopy(patch))
        profiles = merged
    return profiles


def load_profiles() -> list[dict[str, Any]]:
    try:
        sys.path.insert(0, str(ROOT_DIR))
        from backend.app.verticals import list_vertical_profiles  # type: ignore
        return list_vertical_profiles()
    except Exception as exc:
        print(f"[vertical-profiles:warn] backend import failed ({exc}); using static AST fallback", file=sys.stderr)
        return _fallback_profiles()


def strongest_vertical_ids() -> list[str]:
    try:
        return list(_literal_assignment(VERTICAL_10X_SOURCE, "_STRONGEST_VERTICAL_IDS"))
    except Exception:
        return []


def build_index(profiles: list[dict[str, Any]]) -> list[dict[str, Any]]:
    strongest = strongest_vertical_ids()
    items: list[dict[str, Any]] = []
    for profile in profiles:
        vertical_id = str(profile.get("id") or "").strip()
        if not vertical_id:
            continue
        is_strongest = bool(profile.get("is_strongest_vertical")) or vertical_id in strongest
        strongest_rank = profile.get("strongest_rank")
        if strongest_rank is None and vertical_id in strongest:
            strongest_rank = strongest.index(vertical_id) + 1
        aliases = [vertical_id]
        for value in [profile.get("name"), profile.get("short_name")]:
            if value and str(value) not in aliases:
                aliases.append(str(value))
        items.append({
            "id": vertical_id,
            "name": profile.get("name"),
            "short_name": profile.get("short_name"),
            "aliases": aliases,
            "is_strongest_vertical": is_strongest or None,
            "strongest_rank": strongest_rank,
            "file": f"profiles/{vertical_id}.json",
        })
    return items


def write_profiles(profiles: list[dict[str, Any]], target_dir: Path) -> None:
    target_dir.mkdir(parents=True, exist_ok=True)
    expected = {f"{profile.get('id')}.json" for profile in profiles if profile.get("id")}
    for stale in target_dir.glob("*.json"):
        if stale.name not in expected:
            stale.unlink()
    for profile in profiles:
        vertical_id = str(profile.get("id") or "").strip()
        if not vertical_id:
            continue
        (target_dir / f"{vertical_id}.json").write_text(
            json.dumps(profile, ensure_ascii=False, indent=2, sort_keys=False) + "\n",
            encoding="utf-8",
        )


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Export backend vertical profiles for frontend fallback catalog.")
    parser.add_argument("--profiles-dir", type=Path, help="Optional directory for individual profile JSON files.")
    args = parser.parse_args(argv)
    profiles = load_profiles()
    if args.profiles_dir:
        write_profiles(profiles, args.profiles_dir)
    print(json.dumps(build_index(profiles), ensure_ascii=False, indent=2, sort_keys=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
