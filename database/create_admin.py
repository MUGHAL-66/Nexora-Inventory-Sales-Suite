"""Create an initial administrator using a securely prompted password."""

from __future__ import annotations

import getpass
import os

import bcrypt

from database.connection import DatabaseConfigurationError, get_connection
from utils.validators import validate_email, validate_required_text


def create_initial_admin() -> None:
    """Create an administrator only when one with the chosen username is absent."""
    username = os.environ.get("INITIAL_ADMIN_USERNAME", "").strip()
    email = os.environ.get("INITIAL_ADMIN_EMAIL", "").strip()
    full_name = os.environ.get("INITIAL_ADMIN_FULL_NAME", "").strip()
    if not username or not email or not full_name:
        raise DatabaseConfigurationError(
            "Set INITIAL_ADMIN_USERNAME, INITIAL_ADMIN_EMAIL, and "
            "INITIAL_ADMIN_FULL_NAME before creating an administrator."
        )
    username = validate_required_text(username, "Initial admin username", 80)
    email = validate_email(email)
    full_name = validate_required_text(full_name, "Initial admin full name", 160)

    password = getpass.getpass("New administrator password (12+ characters): ")
    confirmation = getpass.getpass("Confirm password: ")
    if len(password) < 12 or len(password.encode("utf-8")) > 72 or password != confirmation:
        raise ValueError(
            "Passwords must match, contain at least 12 characters, and fit within bcrypt's 72-byte limit."
        )
    password_hash = bcrypt.hashpw(password.encode("utf-8"), bcrypt.gensalt()).decode("utf-8")

    with get_connection() as connection:
        cursor = connection.cursor()
        cursor.execute(
            """
            INSERT INTO users (username, email, password_hash, full_name, role)
            VALUES (%s, %s, %s, %s, 'admin')
            """,
            (username, email, password_hash, full_name),
        )
        connection.commit()
        cursor.close()


if __name__ == "__main__":
    create_initial_admin()
    print("Administrator created.")
