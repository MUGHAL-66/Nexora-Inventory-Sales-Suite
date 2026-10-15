from __future__ import annotations

from pathlib import Path

import pytest

from database.connection import (
    DatabaseConfig,
    DatabaseConfigurationError,
    _read_migration_statements,
    _read_schema_statements,
    validate_identifier,
)


def test_database_config_reads_values_and_defaults() -> None:
    config = DatabaseConfig.from_env(
        {"DB_HOST": "localhost", "DB_USER": "app", "DB_PASSWORD": "secret"}
    )
    assert config.database == "inventory_management"
    assert config.port == 3306
    assert config.connection_timeout == 5


def test_database_config_rejects_missing_credentials_without_echoing_values() -> None:
    with pytest.raises(DatabaseConfigurationError, match="DB_HOST"):
        DatabaseConfig.from_env({"DB_PASSWORD": "do-not-echo"})


@pytest.mark.parametrize("value", ["db; DROP DATABASE x", "name with spaces", "`quoted`", ""])
def test_database_identifier_rejects_unsafe_values(value: str) -> None:
    with pytest.raises(DatabaseConfigurationError):
        validate_identifier(value)


def test_database_config_rejects_invalid_port() -> None:
    with pytest.raises(DatabaseConfigurationError, match="integers"):
        DatabaseConfig.from_env(
            {"DB_HOST": "localhost", "DB_USER": "app", "DB_PASSWORD": "secret", "DB_PORT": "bad"}
        )


def test_schema_reader_keeps_first_table_after_leading_comments() -> None:
    schema = Path(__file__).resolve().parents[1] / "database" / "schema.sql"
    statements = _read_schema_statements(schema)
    assert statements[0].startswith("CREATE TABLE IF NOT EXISTS users")
    assert sum(statement.startswith("CREATE TABLE IF NOT EXISTS") for statement in statements) == 11
    migration = _read_migration_statements(schema.parent / "migrations")
    assert len(migration) == 1
    assert migration[0].startswith("ALTER TABLE users")
