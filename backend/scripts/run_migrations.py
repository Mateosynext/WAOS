from __future__ import annotations

from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from app.db import close_connection_pool, execute, fetch_one, get_connection, init_db
from app.utils import utcnow_iso


def main() -> None:
    migrations_dir = ROOT / "db" / "migrations"
    try:
        init_db()
        with get_connection() as conn:
            conn.executescript("CREATE TABLE IF NOT EXISTS schema_migrations (version TEXT PRIMARY KEY, description TEXT, applied_at TEXT NOT NULL);")
            for migration in sorted(migrations_dir.glob("*.sql")):
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
