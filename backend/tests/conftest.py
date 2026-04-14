from __future__ import annotations

import os
from pathlib import Path

# Make the backend test suite hermetic: never inherit a production/staging
# DATABASE_URL from the caller's shell.
TEST_DB_PATH = (Path(__file__).resolve().parents[1] / "test_suite.sqlite3").resolve()

os.environ["APP_ENV"] = "test"
os.environ["ALLOW_SQLITE_FOR_TESTS"] = "true"
os.environ["DATABASE_URL"] = f"sqlite:///{TEST_DB_PATH}"
os.environ.setdefault("APP_SECRET", "waos-test-secret-key-0123456789")
os.environ.setdefault("SECRET_ENCRYPTION_KEY", "waos-test-secret-key-0123456789")
os.environ.setdefault("WAOS_E2E_FAKE_PROVIDERS", "true")


def pytest_sessionstart(session) -> None:
    if TEST_DB_PATH.exists():
        TEST_DB_PATH.unlink()


def pytest_sessionfinish(session, exitstatus) -> None:
    if TEST_DB_PATH.exists():
        TEST_DB_PATH.unlink()
