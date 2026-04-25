from __future__ import annotations

from pathlib import Path
import re
import sys

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))


def migration_sort_key(path: Path) -> tuple[int, str, str]:
    match = re.match(r"^(\d{3})([a-z]?)_", path.name)
    if not match:
        raise ValueError(f"Invalid migration filename {path.name}: expected 3 digits plus optional lowercase suffix, e.g. 005b_name.sql")
    number, suffix = match.groups()
    return (int(number), suffix, path.name)


def list_migrations(migrations_dir: Path) -> list[Path]:
    migrations = sorted(migrations_dir.glob("*.sql"), key=migration_sort_key)
    bare_prefixes: dict[str, list[str]] = {}
    full_prefixes: set[str] = set()
    for migration in migrations:
        match = re.match(r"^(\d{3})([a-z]?)_", migration.name)
        if not match:
            raise ValueError(f"Invalid migration filename {migration.name}")
        number, suffix = match.groups()
        full_prefix = f"{number}{suffix}"
        if full_prefix in full_prefixes:
            raise ValueError(f"Duplicate migration prefix {full_prefix} detected")
        full_prefixes.add(full_prefix)
        if not suffix:
            bare_prefixes.setdefault(number, []).append(migration.name)
    ambiguous = {prefix: names for prefix, names in bare_prefixes.items() if len(names) > 1}
    if ambiguous:
        details = "; ".join(f"{prefix}: {', '.join(names)}" for prefix, names in ambiguous.items())
        raise ValueError(f"Ambiguous migration ordering detected: {details}")
    return migrations


def main() -> None:
    from app.db import close_connection_pool, execute, fetch_one, get_connection, init_db
    from app.utils import utcnow_iso

    migrations_dir = ROOT / "db" / "migrations"
    try:
        init_db()
        with get_connection() as conn:
            conn.executescript("CREATE TABLE IF NOT EXISTS schema_migrations (version TEXT PRIMARY KEY, description TEXT, applied_at TEXT NOT NULL);")
            for migration in list_migrations(migrations_dir):
                version = migration.stem
                already = fetch_one(conn, "SELECT version FROM schema_migrations WHERE version = ?", (version,))
                if already:
                    continue
                conn.executescript(migration.read_text(encoding="utf-8"))
                execute(conn, "INSERT INTO schema_migrations (version, description, applied_at) VALUES (?, ?, ?)", (version, migration.name, utcnow_iso()))
                print(f"[OK] applied {version}")
    finally:
        close_connection_pool()


if __name__ == "__main__":
    main()
