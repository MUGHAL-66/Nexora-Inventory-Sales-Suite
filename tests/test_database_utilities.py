from __future__ import annotations

import mysql.connector

from database import connection as database_connection


class FakeConnection:
    def __init__(self) -> None:
        self.closed = False

    def close(self) -> None:
        self.closed = True


def test_get_connection_closes_connection_after_success(monkeypatch) -> None:
    fake = FakeConnection()
    monkeypatch.setattr(database_connection, "_connect", lambda: fake)

    with database_connection.get_connection() as connection:
        assert connection is fake
        assert fake.closed is False

    assert fake.closed is True


def test_get_connection_closes_connection_after_error(monkeypatch) -> None:
    fake = FakeConnection()
    monkeypatch.setattr(database_connection, "_connect", lambda: fake)

    try:
        with database_connection.get_connection():
            raise RuntimeError("operation failed")
    except RuntimeError:
        pass

    assert fake.closed is True


def test_connect_enables_autocommit_for_service_owned_transactions(monkeypatch) -> None:
    config = database_connection.DatabaseConfig(
        host="localhost",
        port=3306,
        user="app",
        password="test-only",
        database="nexora_inventory",
    )
    captured: dict[str, object] = {}
    expected_connection = object()

    def fake_from_env(cls: type[database_connection.DatabaseConfig]):
        assert cls is database_connection.DatabaseConfig
        return config

    monkeypatch.setattr(
        database_connection.DatabaseConfig,
        "from_env",
        classmethod(fake_from_env),
    )

    def fake_connect(**options):
        captured.update(options)
        return expected_connection

    monkeypatch.setattr(mysql.connector, "connect", fake_connect)

    assert database_connection._connect() is expected_connection
    assert captured["autocommit"] is True
