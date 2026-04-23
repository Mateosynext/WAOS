from __future__ import annotations

import ast
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1] / 'app'
LEGACY_ROOT = ROOT / 'legacy'
FORBIDDEN_PREFIX = 'backend.app.legacy'
LEGACY_FILES = [
    LEGACY_ROOT / 'platform.py',
    LEGACY_ROOT / 'repositories.py',
    LEGACY_ROOT / 'schemas.py',
    LEGACY_ROOT / 'v7.py',
    LEGACY_ROOT / 'v8.py',
    LEGACY_ROOT / 'v9.py',
    LEGACY_ROOT / 'support.py',
]
REMOVED_FROM_ROOT = [
    ROOT / 'platform_legacy.py',
    ROOT / 'repositories_legacy.py',
    ROOT / 'schemas_legacy.py',
    ROOT / 'v7.py',
    ROOT / 'v8.py',
    ROOT / 'v9.py',
    ROOT / 'api' / 'handlers' / 'support_legacy.py',
]


def _imported_names(path: Path) -> list[str]:
    tree = ast.parse(path.read_text(encoding='utf-8'))
    names: list[str] = []
    for node in ast.walk(tree):
        if isinstance(node, ast.ImportFrom):
            module = node.module or ''
            if node.level:
                names.append('.' * node.level + module)
            elif module:
                names.append(module)
        elif isinstance(node, ast.Import):
            names.extend(alias.name for alias in node.names)
    return names


def test_active_modules_do_not_import_legacy_namespace() -> None:
    offenders = []
    for path in ROOT.rglob('*.py'):
        if path.is_relative_to(LEGACY_ROOT):
            continue
        for name in _imported_names(path):
            if name.lstrip('.').startswith(FORBIDDEN_PREFIX):
                offenders.append(f"{path.relative_to(ROOT)} -> {name}")
    assert not offenders, 'Active modules still import legacy namespace: ' + ', '.join(offenders)


def test_legacy_files_are_isolated_under_legacy_package() -> None:
    assert LEGACY_ROOT.is_dir()
    missing = [str(path.relative_to(ROOT)) for path in LEGACY_FILES if not path.exists()]
    assert not missing, 'Missing isolated legacy files: ' + ', '.join(missing)


def test_legacy_files_removed_from_active_root() -> None:
    offenders = [str(path.relative_to(ROOT)) for path in REMOVED_FROM_ROOT if path.exists()]
    assert not offenders, 'Legacy files still leak into active root: ' + ', '.join(offenders)


def test_architecture_manifest_declares_active_sources_of_truth() -> None:
    text = (ROOT / 'architecture.py').read_text(encoding='utf-8')
    for token in ['ARCHITECTURE_SOURCES_OF_TRUTH', 'vertical_transactions', 'vertical_domain_runtime', 'integrations_runtime', 'DEPRECATED_NAMESPACE', 'PLATFORM_OWNERSHIP', 'ROOT_ACTIVE_EXCEPTIONS']:
        assert token in text



def test_no_historical_shims_exist_outside_legacy_package() -> None:
    offenders = sorted(str(path.relative_to(ROOT)) for path in ROOT.glob("*.py") if path.stem in {"v7", "v8", "v9"} or path.name.endswith("_legacy.py"))
    assert not offenders, "Historical compatibility shims still live in the active root: " + ", ".join(offenders)
