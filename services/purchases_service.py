"""Database-backed purchase transactions and supplier cost tracking."""

from __future__ import annotations

import secrets
from datetime import datetime
from decimal import Decimal, ROUND_HALF_UP
from typing import Any

from services.authorization import (
    ADMIN,
    AuthorizationError,
    require_permission,
    PURCHASE_ACCESS,
)
from utils.validators import validate_nonnegative_amount, validate_positive_quantity


def _money(value: Any, field: str) -> Decimal:
    amount = validate_nonnegative_amount(value)
    if amount.as_tuple().exponent < -2:
        raise ValueError(f"{field} may have at most two decimal places.")
    return amount.quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)


def _quantity(value: Any, field: str) -> Decimal:
    quantity = validate_positive_quantity(value)
    if quantity.as_tuple().exponent < -3:
        raise ValueError(f"{field} may have at most three decimal places.")
    return quantity


def _generate_purchase_number() -> str:
    stamp = datetime.now().strftime("%Y%m%d%H%M%S")
    return f"PO-{stamp}-{secrets.token_hex(3).upper()}"


def list_purchases(connection: Any, actor_id: int, *, limit: int = 200) -> list[dict[str, Any]]:
    actor = require_permission(connection, actor_id, PURCHASE_ACCESS)
    if not 1 <= limit <= 500:
        raise ValueError("Purchase limit must be between 1 and 500.")
    cursor = connection.cursor(dictionary=True)
    try:
        financial_columns = ", p.subtotal, p.total" if actor["role"] == ADMIN else ""
        cursor.execute(
            """
            SELECT p.id, p.purchase_number, p.supplier_id, s.name AS supplier_name,
                   p.created_by_user_id, u.full_name AS created_by, p.receiving_status,
                   p.payment_status
            """
            + financial_columns
            + """, p.created_at
            FROM purchases p
            JOIN suppliers s ON s.id = p.supplier_id
            JOIN users u ON u.id = p.created_by_user_id
            ORDER BY p.created_at DESC, p.id DESC
            LIMIT %s
            """,
            (limit,),
        )
        return list(cursor.fetchall())
    finally:
        cursor.close()


def get_purchase_detail(connection: Any, actor_id: int, purchase_id: int) -> dict[str, Any]:
    actor = require_permission(connection, actor_id, PURCHASE_ACCESS)
    is_admin = actor["role"] == ADMIN
    cursor = connection.cursor(dictionary=True)
    try:
        financial_columns = ", p.subtotal, p.total" if is_admin else ""
        cursor.execute(
            """
            SELECT p.id, p.purchase_number, p.supplier_id, s.name AS supplier_name,
                   p.created_by_user_id, u.full_name AS created_by
            """
            + financial_columns
            + """, p.receiving_status, p.payment_status, p.notes, p.created_at
            FROM purchases p
            JOIN suppliers s ON s.id = p.supplier_id
            JOIN users u ON u.id = p.created_by_user_id
            WHERE p.id = %s
            """,
            (purchase_id,),
        )
        purchase = cursor.fetchone()
        if purchase is None:
            raise ValueError("Purchase not found.")
        financial_columns = ", pi.unit_cost, pi.line_total" if is_admin else ""
        cursor.execute(
            """
            SELECT pi.id, prod.sku, prod.name AS product_name, pi.quantity_ordered,
                   pi.quantity_received
            """
            + financial_columns
            + """
            FROM purchase_items pi
            JOIN products prod ON prod.id = pi.product_id
            WHERE pi.purchase_id = %s
            ORDER BY pi.id
            """,
            (purchase_id,),
        )
        purchase["items"] = list(cursor.fetchall())
        return purchase
    finally:
        cursor.close()


def create_purchase(
    connection: Any,
    actor_id: int,
    *,
    supplier_id: int,
    items: list[dict[str, Any]],
    notes: str = "",
    receiving_status: str = "received",
    payment_status: str = "unpaid",
) -> int:
    """Create a purchase, update product stock, and preserve historical cost snapshots."""
    actor = require_permission(connection, actor_id, PURCHASE_ACCESS)
    is_admin = actor["role"] == ADMIN
    if not items:
        raise ValueError("Add at least one product to the purchase.")
    if receiving_status not in ("ordered", "partially_received", "received", "cancelled"):
        raise ValueError("Select a valid receiving status.")
    if payment_status not in ("unpaid", "partially_paid", "paid", "refunded"):
        raise ValueError("Select a valid payment status.")
    cursor = connection.cursor(dictionary=True)
    try:
        connection.start_transaction()
        cursor.execute(
            "SELECT id FROM suppliers WHERE id = %s AND is_active = TRUE",
            (supplier_id,),
        )
        if cursor.fetchone() is None:
            raise ValueError("Supplier not found or inactive.")

        subtotal = Decimal("0.00")
        line_rows: list[dict[str, Any]] = []
        for item in items:
            product_id = int(item["product_id"])
            ordered_quantity = _quantity(item.get("quantity_ordered", item.get("quantity_received")), "Quantity")
            received_quantity = _quantity(
                item.get("quantity_received", ordered_quantity),
                "Received quantity",
            )
            if received_quantity > ordered_quantity:
                raise ValueError("Received quantity cannot exceed ordered quantity.")
            if not is_admin and "unit_cost" in item:
                raise AuthorizationError("Managers cannot set purchase costs.")
            product = get_product_for_purchase_update(cursor, product_id)
            if product["is_active"] is not True:
                raise ValueError(f"Product {product['sku']} is not active.")
            unit_cost = (
                _money(item.get("unit_cost"), "Unit cost")
                if is_admin
                else _money(product["cost_price"], "Unit cost")
            )
            line_total = (ordered_quantity * unit_cost).quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)
            subtotal += line_total
            line_rows.append(
                {
                    "product_id": product_id,
                    "sku": product["sku"],
                    "ordered_quantity": ordered_quantity,
                    "received_quantity": received_quantity,
                    "unit_cost": unit_cost,
                    "line_total": line_total,
                    "existing_stock": product["current_stock"],
                }
            )
        total = subtotal.quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)
        purchase_number = _generate_purchase_number()
        cursor.execute(
            """
            INSERT INTO purchases (purchase_number, supplier_id, created_by_user_id,
                                  subtotal, total, receiving_status, payment_status, notes)
            VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
            """,
            (
                purchase_number,
                supplier_id,
                actor_id,
                subtotal,
                total,
                receiving_status,
                payment_status,
                notes.strip()[:500] if notes else None,
            ),
        )
        purchase_id = int(cursor.lastrowid)
        for row in line_rows:
            cursor.execute(
                """
                INSERT INTO purchase_items
                    (purchase_id, product_id, quantity_ordered, quantity_received,
                     unit_cost, line_total)
                VALUES (%s, %s, %s, %s, %s, %s)
                """,
                (
                    purchase_id,
                    row["product_id"],
                    row["ordered_quantity"],
                    row["received_quantity"],
                    row["unit_cost"],
                    row["line_total"],
                ),
            )
            adjusted_stock = row["existing_stock"] + row["received_quantity"]
            cursor.execute(
                "UPDATE products SET current_stock = %s, cost_price = %s WHERE id = %s",
                (adjusted_stock, row["unit_cost"], row["product_id"]),
            )
            cursor.execute(
                """
                INSERT INTO inventory_transactions
                    (product_id, performed_by_user_id, transaction_type,
                     quantity_change, stock_after, reference_type, reference_id, notes)
                VALUES (%s, %s, 'purchase_received', %s, %s, 'purchase', %s, %s)
                """,
                (
                    row["product_id"],
                    actor_id,
                    row["received_quantity"],
                    adjusted_stock,
                    purchase_id,
                    f"Purchase {purchase_number}",
                ),
            )
        connection.commit()
        return purchase_id
    except Exception:
        connection.rollback()
        raise
    finally:
        cursor.close()


def get_product_for_purchase_update(cursor: Any, product_id: int) -> dict[str, Any]:
    cursor.execute(
        """
        SELECT id, sku, name, cost_price, selling_price, current_stock, is_active
        FROM products WHERE id = %s FOR UPDATE
        """,
        (product_id,),
    )
    product = cursor.fetchone()
    if product is None:
        raise ValueError("Product not found.")
    return product
