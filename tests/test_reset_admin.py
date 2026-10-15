from __future__ import annotations

from contextlib import contextmanager
from types import SimpleNamespace
from typing import Any

import bcrypt
import pytest

import reset_admin


class FakeCursor:
    def __init__(self, accounts: list[dict[str, Any]], *, update_rowcount: int = 1) -> None:
        self.accounts = accounts
        self.update_rowcount = update_rowcount
        self.rowcount = 0
        self.statements: list[tuple[str, tuple]] = []
        self.closed = False
        self.password_hash: str | None = None

    def execute(self, query: str, parameters: tuple = ()) -> None:
        self.statements.append((query, parameters))
        if query.lstrip().startswith("UPDATE users"):
            self.password_hash = parameters[0]
            self.rowcount = self.update_rowcount

    def fetchall(self) -> list[dict[str, Any]]:
        return self.accounts

    def close(self) -> None:
        self.closed = True


class FakeConnection:
    def __init__(self, cursor: FakeCursor) -> None:
        self.fake_cursor = cursor
        self.commits = 0
        self.rollbacks = 0
        self.transactions = 0

    def cursor(self, *, dictionary: bool = False) -> FakeCursor:
        assert dictionary
        return self.fake_cursor

    def start_transaction(self) -> None:
        self.transactions += 1

    def commit(self) -> None:
        self.commits += 1

    def rollback(self) -> None:
        self.rollbacks += 1


def install_fake_connection(
    monkeypatch: pytest.MonkeyPatch,
    accounts: list[dict[str, Any]],
    *,
    database: str = "nexora_inventory",
    update_rowcount: int = 1,
) -> FakeConnection:
    cursor = FakeCursor(accounts, update_rowcount=update_rowcount)
    connection = FakeConnection(cursor)

    @contextmanager
    def fake_get_connection():
        yield connection

    def fake_from_env(cls: type[reset_admin.DatabaseConfig]) -> SimpleNamespace:
        assert cls is reset_admin.DatabaseConfig
        return SimpleNamespace(database=database)

    def fake_getpass(prompt: str) -> str:
        assert prompt
        return "a sufficiently long password"

    monkeypatch.setattr(
        reset_admin.DatabaseConfig,
        "from_env",
        classmethod(fake_from_env),
    )
    monkeypatch.setattr(reset_admin, "get_connection", fake_get_connection)
    monkeypatch.setattr(reset_admin.getpass, "getpass", fake_getpass)
    return connection


def active_admin() -> dict[str, Any]:
    return {"id": 1, "role": "admin", "is_active": True}


def test_reset_updates_only_admin_password_hash_and_commits(monkeypatch: pytest.MonkeyPatch) -> None:
    connection = install_fake_connection(monkeypatch, [active_admin()])

    reset_admin.reset_admin_password()

    cursor = connection.fake_cursor
    assert connection.transactions == 1
    assert connection.commits == 1
    assert connection.rollbacks == 0
    assert cursor.closed
    assert bcrypt.checkpw(
        b"a sufficiently long password", cursor.password_hash.encode("utf-8")
    )
    update_query, update_parameters = cursor.statements[1]
    assert "SET password_hash = %s" in update_query
    assert "WHERE id = %s AND username = %s" in update_query
    assert update_parameters[1:] == (1, "admin")


@pytest.mark.parametrize(
    "accounts,error",
    [
        ([], "exactly one"),
        ([active_admin(), active_admin()], "exactly one"),
        ([{"id": 1, "role": "sales_staff", "is_active": True}], "role"),
        ([{"id": 1, "role": "admin", "is_active": False}], "inactive"),
    ],
)
def test_reset_rejects_unsafe_account_state(
    monkeypatch: pytest.MonkeyPatch,
    accounts: list[dict[str, Any]],
    error: str,
) -> None:
    connection = install_fake_connection(monkeypatch, accounts)

    with pytest.raises(reset_admin.AdminResetError, match=error):
        reset_admin.reset_admin_password()

    assert connection.commits == 0
    assert connection.rollbacks == 1
    assert connection.fake_cursor.password_hash is None
    assert connection.fake_cursor.closed


def test_reset_refuses_unexpected_database_before_prompting(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    install_fake_connection(monkeypatch, [active_admin()], database="another_database")

    def unexpected_prompt(prompt: str) -> str:
        pytest.fail(f"Password prompt should not run for the wrong database: {prompt}")

    monkeypatch.setattr(reset_admin.getpass, "getpass", unexpected_prompt)
    with pytest.raises(reset_admin.AdminResetError, match="DB_NAME"):
        reset_admin.reset_admin_password()


@pytest.mark.parametrize(
    "responses,error",
    [
        (["a sufficiently long password", "a different long password"], "do not match"),
        (["too short", "too short"], "at least 12"),
        (["é" * 37, "é" * 37], "72 UTF-8 bytes"),
    ],
)
def test_password_prompt_enforces_existing_policy(
    monkeypatch: pytest.MonkeyPatch,
    responses: list[str],
    error: str,
) -> None:
    prompts = iter(responses)
    monkeypatch.setattr(reset_admin.getpass, "getpass", lambda prompt: (prompt, next(prompts))[1])

    with pytest.raises(reset_admin.AdminResetError, match=error):
        reset_admin._prompt_for_password()


def test_reset_rolls_back_when_update_does_not_affect_one_row(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    connection = install_fake_connection(
        monkeypatch, [active_admin()], update_rowcount=0
    )

    with pytest.raises(reset_admin.AdminResetError, match="updated 0"):
        reset_admin.reset_admin_password()

    assert connection.commits == 0
    assert connection.rollbacks == 1
    assert connection.fake_cursor.closed
