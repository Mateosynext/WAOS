from __future__ import annotations

import os
import sys
from pathlib import Path

# Make the backend test suite hermetic: never inherit a production/staging
# DATABASE_URL from the caller's shell.
TEST_DB_PATH = (Path(__file__).resolve().parents[1] / "test_suite.sqlite3").resolve()
REPO_ROOT = Path(__file__).resolve().parents[2]
BACKEND_ROOT = Path(__file__).resolve().parents[1]
for candidate in (str(REPO_ROOT), str(BACKEND_ROOT)):
    if candidate not in sys.path:
        sys.path.insert(0, candidate)

os.environ["APP_ENV"] = "test"
os.environ["ALLOW_SQLITE_FOR_TESTS"] = "true"
os.environ["DATABASE_URL"] = f"sqlite:///{TEST_DB_PATH}"
os.environ.setdefault("APP_SECRET", "waos-test-secret-key-0123456789XYZ")
os.environ.setdefault("SECRET_ENCRYPTION_KEY", "waos-test-secret-key-0123456789XYZ")
os.environ.setdefault("WAOS_E2E_FAKE_PROVIDERS", "true")
os.environ.setdefault("WAOS_OPERATIONAL_CONTROL_NOW", "2026-04-16T12:00:00Z")


def pytest_sessionstart(session) -> None:
    if TEST_DB_PATH.exists():
        TEST_DB_PATH.unlink()


def pytest_sessionfinish(session, exitstatus) -> None:
    if TEST_DB_PATH.exists():
        TEST_DB_PATH.unlink()
