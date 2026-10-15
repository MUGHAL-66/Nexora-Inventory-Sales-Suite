"""Safely reset the existing admin account password."""

from __future__ import annotations

import getpass
import sys
from typing import Any

import bcrypt

from database.connection import DatabaseConfig, DatabaseConfigurationError, get_connection

_EXPECTED_DATABASE = "nexora_inventory"
_ADMIN_USERNAME = "admin"


class AdminResetError(ValueError):
    """Raised when the admin account is not safe to update."""


def _prompt_for_password() -> str:
    password = getpass.getpass("New admin password (12+ characters): ")
    confirmation = getpass.getpass("Confirm new password: ")
    if password != confirmation:
        raise AdminResetError("Passwords do not match.")
    if len(password) < 12:
        raise AdminResetError("Password must contain at least 12 characters.")
    if len(password.encode("utf-8")) > 72:
        raise AdminResetError("Password must be no longer than 72 UTF-8 bytes.")
    return password


def reset_admin_password() -> None:
    """Update only the existing, active admin account's bcrypt password hash."""
    config = DatabaseConfig.from_env()
    if config.database != _EXPECTED_DATABASE:
        raise AdminResetError(
            f"Refusing to continue: DB_NAME must be '{_EXPECTED_DATABASE}'."
        )

    password = _prompt_for_password()
    password_hash = bcrypt.hashpw(password.encode("utf-8"), bcrypt.gensalt()).decode("utf-8")

    with get_connection() as connection:
        cursor: Any = connection.cursor(dictionary=True)
        try:
            connection.start_transaction()
            cursor.execute(
                """
                SELECT id, role, is_active
                FROM users
                WHERE username = %s
                FOR UPDATE
                """,
                (_ADMIN_USERNAME,),
            )
            accounts = cursor.fetchall()
            if len(accounts) != 1:
                raise AdminResetError(
                    f"Expected exactly one '{_ADMIN_USERNAME}' account; found {len(accounts)}."
                )

            account = accounts[0]
            account_issues = []
            if account["role"] != "admin":
                account_issues.append("the account role is not 'admin'")
            if not account["is_active"]:
                account_issues.append("the account is inactive")
            if account_issues:
                raise AdminResetError(
                    "Cannot reset the account because " + " and ".join(account_issues) + "."
                )

            cursor.execute(
                """
                UPDATE users
                SET password_hash = %s
                WHERE id = %s AND username = %s
                """,
                (password_hash, account["id"], _ADMIN_USERNAME),
            )
            if cursor.rowcount != 1:
                raise AdminResetError(
                    "Expected to update exactly one admin account; "
                    f"updated {cursor.rowcount}."
                )
            connection.commit()
        except BaseException:
            connection.rollback()
            raise
        finally:
            cursor.close()


def main() -> int:
    try:
        reset_admin_password()
    except (AdminResetError, DatabaseConfigurationError) as exc:
        print(f"Admin password reset failed: {exc}", file=sys.stderr)
        return 1
    except Exception as exc:
        print(
            "Admin password reset failed due to a database or internal error "
            f"({type(exc).__name__}).",
            file=sys.stderr,
        )
        return 1

    print("Admin password reset successfully.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
