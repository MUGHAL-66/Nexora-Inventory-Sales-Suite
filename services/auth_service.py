"""Authentication and administrative user account operations."""

from __future__ import annotations

from typing import Any

import bcrypt
from mysql.connector.errors import IntegrityError

from services.authorization import ADMIN, SUPPORTED_USER_ROLES, require_admin
from utils.validators import validate_email, validate_required_text


def authenticate(connection: Any, username: str, password: str) -> dict[str, Any] | None:
    """Authenticate credentials and return a minimal session-safe user record."""
    normalized_username = username.strip()
    if not normalized_username or not password:
        return None
    cursor = connection.cursor(dictionary=True)
    try:
        cursor.execute(
            """
            SELECT id, username, full_name, password_hash, role, is_active
            FROM users WHERE username = %s
            """,
            (normalized_username,),
        )
        record = cursor.fetchone()
    finally:
        cursor.close()
    if not record or not record["is_active"]:
        return None
    try:
        valid = bcrypt.checkpw(password.encode("utf-8"), record["password_hash"].encode("utf-8"))
    except (ValueError, TypeError):
        valid = False
    if not valid:
        return None
    if record["role"] not in SUPPORTED_USER_ROLES:
        return None
    return {
        "id": record["id"],
        "username": record["username"],
        "full_name": record["full_name"],
        "role": record["role"],
    }


def get_active_user(connection: Any, user_id: int) -> dict[str, Any] | None:
    """Revalidate a Streamlit session identity against current database state."""
    cursor = connection.cursor(dictionary=True)
    try:
        cursor.execute(
            "SELECT id, username, full_name, role, is_active FROM users WHERE id = %s",
            (user_id,),
        )
        user = cursor.fetchone()
    finally:
        cursor.close()
    if user is None or not user["is_active"]:
        return None
    if user["role"] not in SUPPORTED_USER_ROLES:
        return None
    return {
        "id": user["id"],
        "username": user["username"],
        "full_name": user["full_name"],
        "role": user["role"],
    }


def create_user(
    connection: Any,
    actor_id: int,
    *,
    username: str,
    email: str,
    full_name: str,
    role: str,
    password: str,
) -> int:
    """Create an admin-managed user with a bcrypt password hash."""
    require_admin(connection, actor_id)
    username = validate_required_text(username, "Username", 80)
    email = validate_email(email)
    full_name = validate_required_text(full_name, "Full name", 160)
    if role not in SUPPORTED_USER_ROLES:
        raise ValueError("Choose Admin, Manager, Sales Staff, or Staff for the user role.")
    if len(password) < 12:
        raise ValueError("Password must contain at least 12 characters.")
    if len(password.encode("utf-8")) > 72:
        raise ValueError("Password must be no longer than 72 UTF-8 bytes.")
    password_hash = bcrypt.hashpw(password.encode("utf-8"), bcrypt.gensalt()).decode("utf-8")
    cursor = connection.cursor()
    try:
        cursor.execute(
            """
            INSERT INTO users (username, email, full_name, password_hash, role)
            VALUES (%s, %s, %s, %s, %s)
            """,
            (username, email, full_name, password_hash, role),
        )
        connection.commit()
        return int(cursor.lastrowid)
    except IntegrityError as exc:
        connection.rollback()
        if exc.errno == 1062:
            raise ValueError("That username or email is already in use.") from exc
        raise
    finally:
        cursor.close()


def list_users(connection: Any, actor_id: int) -> list[dict[str, Any]]:
    require_admin(connection, actor_id)
    cursor = connection.cursor(dictionary=True)
    try:
        cursor.execute(
            """
            SELECT id, username, email, full_name, role, is_active, created_at
            FROM users ORDER BY full_name, id
            """
        )
        return list(cursor.fetchall())
    finally:
        cursor.close()


def deactivate_user(connection: Any, actor_id: int, target_user_id: int) -> None:
    """Deactivate another user, preserving at least one active administrator."""
    require_admin(connection, actor_id)
    if actor_id == target_user_id:
        raise ValueError("You cannot deactivate your own account.")
    cursor = connection.cursor(dictionary=True)
    try:
        connection.start_transaction()
        cursor.execute(
            "SELECT id, role, is_active FROM users WHERE id = %s FOR UPDATE",
            (target_user_id,),
        )
        target = cursor.fetchone()
        if target is None:
            raise ValueError("User not found.")
        if not target["is_active"]:
            raise ValueError("This user is already inactive.")
        if target["role"] == ADMIN:
            cursor.execute(
                "SELECT id FROM users WHERE role = 'admin' AND is_active = TRUE FOR UPDATE"
            )
            if len(cursor.fetchall()) <= 1:
                raise ValueError("The last active administrator cannot be deactivated.")
        cursor.execute("UPDATE users SET is_active = FALSE WHERE id = %s", (target_user_id,))
        connection.commit()
    except Exception:
        connection.rollback()
        raise
    finally:
        cursor.close()
