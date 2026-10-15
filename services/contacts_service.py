"""Database-backed customer and supplier directory operations."""

from __future__ import annotations

import secrets
from typing import Any

from mysql.connector.errors import IntegrityError

from services.authorization import (
    ADMIN,
    require_admin,
    require_customer_access,
    require_supplier_access,
)
from utils.validators import (
    validate_email,
    validate_optional_text,
    validate_phone,
    validate_required_text,
)


def _prepare_contact(
    *, name: str, email: str, phone: str, address: str
) -> tuple[str, str | None, str | None, str | None]:
    normalized_name = validate_required_text(name, "Name", 160)
    normalized_email = validate_email(email) if email.strip() else None
    normalized_phone = validate_phone(phone)
    normalized_address = validate_optional_text(address, "Address", 4000)
    return normalized_name, normalized_email, normalized_phone, normalized_address


def _ensure_email_available(
    connection: Any, *, table: str, email: str | None, record_id: int | None
) -> None:
    if email is None:
        return
    if table not in ("customers", "suppliers"):
        raise ValueError("Unsupported contact type.")
    cursor = connection.cursor()
    try:
        if record_id is None:
            cursor.execute(
                f"SELECT id FROM {table} WHERE email = %s AND is_active = TRUE LIMIT 1",
                (email,),
            )
        else:
            cursor.execute(
                f"SELECT id FROM {table} WHERE email = %s AND is_active = TRUE AND id <> %s LIMIT 1",
                (email, record_id),
            )
        if cursor.fetchone() is not None:
            raise ValueError("An active record already uses that email address.")
    finally:
        cursor.close()


def list_customers(
    connection: Any, actor_id: int, *, search: str = "", active_only: bool = True
) -> list[dict[str, Any]]:
    require_customer_access(connection, actor_id)
    clauses: list[str] = []
    parameters: list[Any] = []
    if active_only:
        clauses.append("c.is_active = TRUE")
    normalized = search.strip()
    if normalized:
        wildcard = f"%{normalized}%"
        clauses.append("(c.name LIKE %s OR c.email LIKE %s OR c.phone LIKE %s)")
        parameters.extend((wildcard, wildcard, wildcard))
    where = " WHERE " + " AND ".join(clauses) if clauses else ""
    cursor = connection.cursor(dictionary=True)
    try:
        cursor.execute(
            """
            SELECT c.id, c.customer_code, c.name, c.email, c.phone, c.address,
                   c.is_active, c.created_at, c.updated_at,
                   COUNT(DISTINCT s.id) AS sale_count,
                   COALESCE(SUM(CASE WHEN s.sale_status = 'completed' THEN s.total ELSE 0 END), 0)
                       AS lifetime_sales
            FROM customers c LEFT JOIN sales s ON s.customer_id = c.id
            """
            + where
            + " GROUP BY c.id ORDER BY c.name, c.id",
            tuple(parameters),
        )
        return list(cursor.fetchall())
    finally:
        cursor.close()


def save_customer(
    connection: Any,
    actor_id: int,
    *,
    name: str,
    email: str = "",
    phone: str = "",
    address: str = "",
    customer_id: int | None = None,
) -> int:
    require_customer_access(connection, actor_id)
    contact = _prepare_contact(name=name, email=email, phone=phone, address=address)
    _ensure_email_available(connection, table="customers", email=contact[1], record_id=customer_id)
    cursor = connection.cursor()
    try:
        if customer_id is None:
            code = f"CUS-{secrets.token_hex(6).upper()}"
            cursor.execute(
                """
                INSERT INTO customers (customer_code, name, email, phone, address)
                VALUES (%s, %s, %s, %s, %s)
                """,
                (code, *contact),
            )
            customer_id = int(cursor.lastrowid)
        else:
            cursor.execute("SELECT id FROM customers WHERE id = %s", (customer_id,))
            if cursor.fetchone() is None:
                raise ValueError("Customer not found.")
            cursor.execute(
                """
                UPDATE customers SET name = %s, email = %s, phone = %s, address = %s
                WHERE id = %s
                """,
                (*contact, customer_id),
            )
        connection.commit()
        return customer_id
    except IntegrityError as exc:
        connection.rollback()
        if exc.errno == 1062:
            raise ValueError("A customer record with those details already exists.") from exc
        raise
    finally:
        cursor.close()


def set_customer_active(connection: Any, actor_id: int, customer_id: int, active: bool) -> None:
    require_customer_access(connection, actor_id)
    cursor = connection.cursor()
    try:
        cursor.execute("UPDATE customers SET is_active = %s WHERE id = %s", (active, customer_id))
        if cursor.rowcount == 0:
            raise ValueError("Customer not found or already has that status.")
        connection.commit()
    finally:
        cursor.close()


def list_customer_history(
    connection: Any, actor_id: int, customer_id: int
) -> list[dict[str, Any]]:
    require_customer_access(connection, actor_id)
    cursor = connection.cursor(dictionary=True)
    try:
        cursor.execute(
            """
            SELECT s.invoice_number, s.created_at, s.total, s.payment_status, s.sale_status,
                   u.full_name AS staff_name
            FROM sales s JOIN users u ON u.id = s.staff_user_id
            WHERE s.customer_id = %s
            ORDER BY s.created_at DESC, s.id DESC LIMIT 100
            """,
            (customer_id,),
        )
        return list(cursor.fetchall())
    finally:
        cursor.close()


def list_suppliers(
    connection: Any, actor_id: int, *, search: str = "", active_only: bool = True
) -> list[dict[str, Any]]:
    actor = require_supplier_access(connection, actor_id)
    clauses: list[str] = []
    parameters: list[Any] = []
    if active_only:
        clauses.append("s.is_active = TRUE")
    normalized = search.strip()
    if normalized:
        wildcard = f"%{normalized}%"
        clauses.append("(s.name LIKE %s OR s.email LIKE %s OR s.phone LIKE %s)")
        parameters.extend((wildcard, wildcard, wildcard))
    where = " WHERE " + " AND ".join(clauses) if clauses else ""
    cursor = connection.cursor(dictionary=True)
    try:
        if actor["role"] == ADMIN:
            cursor.execute(
                """
                SELECT s.id, s.supplier_code, s.name, s.email, s.phone, s.address,
                       s.is_active, s.created_at, s.updated_at,
                       COUNT(DISTINCT p.id) AS purchase_count,
                       COALESCE(SUM(CASE WHEN p.receiving_status <> 'cancelled'
                                         THEN p.total ELSE 0 END), 0) AS purchase_total
                FROM suppliers s LEFT JOIN purchases p ON p.supplier_id = s.id
                """
                + where
                + " GROUP BY s.id ORDER BY s.name, s.id",
                tuple(parameters),
            )
        else:
            cursor.execute(
                """
                SELECT s.id, s.supplier_code, s.name, s.email, s.phone, s.address,
                       s.is_active, s.created_at, s.updated_at
                FROM suppliers s
                """
                + where
                + " ORDER BY s.name, s.id",
                tuple(parameters),
            )
        return list(cursor.fetchall())
    finally:
        cursor.close()


def save_supplier(
    connection: Any,
    actor_id: int,
    *,
    name: str,
    email: str = "",
    phone: str = "",
    address: str = "",
    supplier_id: int | None = None,
) -> int:
    require_supplier_access(connection, actor_id)
    contact = _prepare_contact(name=name, email=email, phone=phone, address=address)
    _ensure_email_available(connection, table="suppliers", email=contact[1], record_id=supplier_id)
    cursor = connection.cursor()
    try:
        if supplier_id is None:
            code = f"SUP-{secrets.token_hex(6).upper()}"
            cursor.execute(
                """
                INSERT INTO suppliers (supplier_code, name, email, phone, address)
                VALUES (%s, %s, %s, %s, %s)
                """,
                (code, *contact),
            )
            supplier_id = int(cursor.lastrowid)
        else:
            cursor.execute("SELECT id FROM suppliers WHERE id = %s", (supplier_id,))
            if cursor.fetchone() is None:
                raise ValueError("Supplier not found.")
            cursor.execute(
                """
                UPDATE suppliers SET name = %s, email = %s, phone = %s, address = %s
                WHERE id = %s
                """,
                (*contact, supplier_id),
            )
        connection.commit()
        return supplier_id
    except IntegrityError as exc:
        connection.rollback()
        if exc.errno == 1062:
            raise ValueError("A supplier record with those details already exists.") from exc
        raise
    finally:
        cursor.close()


def set_supplier_active(connection: Any, actor_id: int, supplier_id: int, active: bool) -> None:
    require_supplier_access(connection, actor_id)
    cursor = connection.cursor()
    try:
        cursor.execute("UPDATE suppliers SET is_active = %s WHERE id = %s", (active, supplier_id))
        if cursor.rowcount == 0:
            raise ValueError("Supplier not found or already has that status.")
        connection.commit()
    finally:
        cursor.close()


def list_supplier_history(
    connection: Any, actor_id: int, supplier_id: int
) -> list[dict[str, Any]]:
    require_admin(connection, actor_id)
    cursor = connection.cursor(dictionary=True)
    try:
        cursor.execute(
            """
            SELECT p.purchase_number, p.created_at, p.total, p.payment_status,
                   p.receiving_status, u.full_name AS created_by
            FROM purchases p JOIN users u ON u.id = p.created_by_user_id
            WHERE p.supplier_id = %s
            ORDER BY p.created_at DESC, p.id DESC LIMIT 100
            """,
            (supplier_id,),
        )
        return list(cursor.fetchall())
    finally:
        cursor.close()
