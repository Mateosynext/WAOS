from __future__ import annotations

from .schema_sql import apply_schema_sql

PLATFORM_SCHEMA_SQL_FILES = [
    "001_world_class.sql",
    "002_world_class_plus.sql",
    "003_telemetry.sql",
]

GUIDED_VERTICAL_ONBOARDING_COLUMN_ENSURES = [('vertical_onboarding_wizards', 'validation_snapshot_json', "TEXT NOT NULL DEFAULT '{}'"),
 ('vertical_onboarding_wizards', 'recompute_state_json', "TEXT NOT NULL DEFAULT '{}'"),
 ('vertical_onboarding_wizards', 'wizard_revision', 'INTEGER NOT NULL DEFAULT 1')]


def apply_platform_schema_governance_migration(conn, ensure_column) -> None:
    for filename in PLATFORM_SCHEMA_SQL_FILES:
        apply_schema_sql(conn, "platform", filename)
    for table, column, definition in GUIDED_VERTICAL_ONBOARDING_COLUMN_ENSURES:
        ensure_column(conn, table, column, definition)
