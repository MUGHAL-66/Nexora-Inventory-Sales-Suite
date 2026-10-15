
"""MySQL configuration, connection management, and safe initialization."""

from __future__ import annotations

import logging
import os
import re
from contextlib import contextmanager
from dataclasses import dataclass
from pathlib import Path
from typing import Generator, Mapping

from dotenv import load_dotenv

LOGGER = logging.getLogger(__name__)
_IDENTIFIER_PATTERN = re.compile(r"^[A-Za-z0-9_]+$")
_PROJECT_ROOT = Path(__file__).resolve().parent.parent

# Load local .env settings. Streamlit Cloud can use st.secrets.
load_dotenv(_PROJECT_ROOT / ".env")


class DatabaseConfigurationError(ValueError):
    """Raised when required database settings are missing or invalid."""


@dataclass(frozen=True)
class DatabaseConfig:
    host: str
    port: int
    user: str
    password: str
    database: str
    connection_timeout: int = 5

    @classmethod
    def from_env(
        cls, environ: Mapping[str, str] | None = None
    ) -> "DatabaseConfig":
        """Load settings from environment variables and Streamlit secrets."""

        if environ is not None:
            values = environ
        else:
            config_values = dict(os.environ)

            # Environment variables take precedence.
            # Missing values can be supplied through Streamlit Cloud Secrets.
            try:
                import streamlit as st

                secret_keys = (
                    "DB_HOST",
                    "DB_PORT",
                    "DB_USER",
                    "DB_PASSWORD",
                    "DB_NAME",
                    "DB_CONNECTION_TIMEOUT",
                )

                for key in secret_keys:
                    if not config_values.get(key) and key in st.secrets:
                        config_values[key] = str(st.secrets[key])

            except Exception:
                # Local development should still work without Streamlit secrets.
                pass

            values = config_values

        required = ("DB_HOST", "DB_USER", "DB_PASSWORD")
        missing = [
            key for key in required
            if not values.get(key, "").strip()
        ]

        if missing:
            raise DatabaseConfigurationError(
                "Database configuration is incomplete. Set: "
                + ", ".join(missing)
            )

        try:
            port = int(values.get("DB_PORT", "3306"))
            timeout = int(values.get("DB_CONNECTION_TIMEOUT", "5"))
        except ValueError as exc:
            raise DatabaseConfigurationError(
                "DB_PORT and DB_CONNECTION_TIMEOUT must be integers."
            ) from exc

        if not 1 <= port <= 65535 or timeout < 1:
            raise DatabaseConfigurationError(
                "DB_PORT must be between 1 and 65535 and "
                "DB_CONNECTION_TIMEOUT must be positive."
            )

        database = values.get(
            "DB_NAME", "inventory_management"
        ).strip()

        validate_identifier(database)

        return cls(
            host=values["DB_HOST"].strip(),
            port=port,
            user=values["DB_USER"].strip(),
            password=values["DB_PASSWORD"],
            database=database,
            connection_timeout=timeout,
        )


def validate_identifier(identifier: str) -> str:
    """Validate SQL identifiers before using them in DDL statements."""
    if not _IDENTIFIER_PATTERN.fullmatch(identifier):
        raise DatabaseConfigurationError(
            "Database name contains unsupported characters."
        )
    return identifier


def _connect(*, include_database: bool = True):
    """Create a MySQL-compatible database connection."""
    config = DatabaseConfig.from_env()

    import mysql.connector

    options = {
        "host": config.host,
        "port": config.port,
        "user": config.user,
        "password": config.password,
        "connection_timeout": config.connection_timeout,
        "charset": "utf8mb4",
        "use_unicode": True,
        "autocommit": True,
    }

    if include_database:
        options["database"] = config.database

    return mysql.connector.connect(**options)


@contextmanager
def get_connection() -> Generator[object, None, None]:
    """Yield a connection and always close it after use."""
    connection = _connect()
    try:
        yield connection
    finally:
        connection.close()


def _read_schema_statements(schema_file: Path) -> list[str]:
    """Read SQL schema statements, excluding full-line comments."""
    schema = schema_file.read_text(encoding="utf-8")

    uncommented = "\n".join(
        line
        for line in schema.splitlines()
        if not line.lstrip().startswith("--")
    )

    return [
        statement.strip()
        for statement in uncommented.split(";")
        if statement.strip()
    ]


def _read_migration_statements(migration_dir: Path) -> list[str]:
    """Read numbered SQL migrations in lexical order."""
    statements: list[str] = []

    for migration_file in sorted(migration_dir.glob("[0-9]*.sql")):
        statements.extend(_read_schema_statements(migration_file))

    return statements


def initialize_database(schema_path: Path | None = None) -> None:
    """Create the configured database and missing tables without dropping data."""
    config = DatabaseConfig.from_env()
    validate_identifier(config.database)

    schema_file = schema_path or Path(__file__).with_name("schema.sql")

    if not schema_file.is_file():
        raise FileNotFoundError(
            f"Database schema file not found: {schema_file}"
        )

    connection = _connect(include_database=False)

    try:
        cursor = connection.cursor()

        cursor.execute(
            f"CREATE DATABASE IF NOT EXISTS `{config.database}` "
            "CHARACTER SET utf8mb4 COLLATE utf8mb4_0900_ai_ci"
        )

        cursor.execute(f"USE `{config.database}`")

        for statement in _read_schema_statements(schema_file):
            cursor.execute(statement)

        migrations = schema_file.parent / "migrations"

        for statement in _read_migration_statements(migrations):
            cursor.execute(statement)

        connection.commit()
        cursor.close()

        LOGGER.info(
            "Database schema initialized safely for database '%s'.",
            config.database,
        )

    finally:
        connection.close()
