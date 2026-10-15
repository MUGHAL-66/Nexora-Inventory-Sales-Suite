"""Database-backed sales transactions and invoice history."""

from __future__ import annotations

import secrets
from datetime import datetime
from decimal import Decimal, ROUND_HALF_UP
from typing import Any

from services.authorization import SALES_ACCESS, require_permission
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


def _generate_invoice_number() -> str:
    stamp = datetime.now().strftime("%Y%m%d%H%M%S")
    return f"INV-{stamp}-{secrets.token_hex(3).upper()}"


def list_sales(connection: Any, actor_id: int, *, limit: int = 200) -> list[dict[str, Any]]:
    require_permission(connection, actor_id, SALES_ACCESS)
    if not 1 <= limit <= 500:
        raise ValueError("Sales limit must be between 1 and 500.")
    cursor = connection.cursor(dictionary=True)
    try:
        cursor.execute(
            """
            SELECT s.id, s.invoice_number, s.customer_id, c.name AS customer_name,
                   s.staff_user_id, u.full_name AS staff_name, s.payment_status,
                   s.sale_status, s.subtotal, s.discount, s.total, s.created_at
            FROM sales s
            LEFT JOIN customers c ON c.id = s.customer_id
            LEFT JOIN users u ON u.id = s.staff_user_id
            ORDER BY s.created_at DESC, s.id DESC
            LIMIT %s
            """,
            (limit,),
        )
        return list(cursor.fetchall())
    finally:
        cursor.close()


def get_sale_detail(connection: Any, actor_id: int, sale_id: int) -> dict[str, Any]:
    require_permission(connection, actor_id, SALES_ACCESS)
    cursor = connection.cursor(dictionary=True)
    try:
        cursor.execute(
            """
            SELECT s.id, s.invoice_number, s.customer_id, c.name AS customer_name,
                   s.staff_user_id, u.full_name AS staff_name, s.subtotal, s.discount,
                   s.total, s.payment_status, s.sale_status, s.notes, s.created_at
            FROM sales s
            LEFT JOIN customers c ON c.id = s.customer_id
            LEFT JOIN users u ON u.id = s.staff_user_id
            WHERE s.id = %s
            """,
            (sale_id,),
        )
        sale = cursor.fetchone()
        if sale is None:
            raise ValueError("Sale not found.")
        cursor.execute(
            """
            SELECT si.id, p.sku, p.name AS product_name, si.quantity, si.unit_price,
                   si.unit_cost, si.line_total
            FROM sale_items si
            JOIN products p ON p.id = si.product_id
            WHERE si.sale_id = %s
            ORDER BY si.id
            """,
            (sale_id,),
        )
        sale["items"] = list(cursor.fetchall())
        return sale
    finally:
        cursor.close()


def create_sale(
    connection: Any,
    actor_id: int,
    *,
    customer_id: int | None,
    items: list[dict[str, Any]],
    discount: Any = 0,
    payment_status: str = "unpaid",
    sale_status: str = "completed",
    notes: str = "",
) -> int:
    """Create a sale, decrement stock, and preserve historical sale snapshots."""
    require_permission(connection, actor_id, SALES_ACCESS)
    if not items:
        raise ValueError("Add at least one product to the sale.")
    if customer_id is not None:
        cursor = connection.cursor(dictionary=True)
        try:
            cursor.execute(
                "SELECT id FROM customers WHERE id = %s AND is_active = TRUE",
                (customer_id,),
            )
            if cursor.fetchone() is None:
                raise ValueError("Customer not found or inactive.")
        finally:
            cursor.close()
    normalized_discount = _money(discount, "Discount")
    if payment_status not in ("unpaid", "partially_paid", "paid", "refunded"):
        raise ValueError("Select a valid payment status.")
    if sale_status not in ("draft", "completed", "voided", "refunded"):
        raise ValueError("Select a valid sale status.")
    normalized_notes = notes.strip()[:500] if notes else ""
    subtotal = Decimal("0.00")
    line_rows: list[dict[str, Any]] = []
    cursor = connection.cursor(dictionary=True)
    transaction_started = False
    try:
        connection.start_transaction()
        transaction_started = True
        for item in items:
            product_id = int(item["product_id"])
            quantity = _quantity(item.get("quantity"), "Quantity")
            product = get_product_for_update(cursor, product_id)
            unit_price = _money(item.get("unit_price", product["selling_price"]), "Unit price")
            line_total = (quantity * unit_price).quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)
            if quantity > product["current_stock"]:
                raise ValueError(f"Only {product['current_stock']} {product['sku']} available.")
            subtotal += line_total
            line_rows.append(
                {
                    "product_id": product_id,
                    "sku": product["sku"],
                    "quantity": quantity,
                    "unit_price": unit_price,
                    "unit_cost": Decimal(str(product["cost_price"])),
                    "line_total": line_total,
                    "available_stock": product["current_stock"],
                }
            )
        total = (subtotal - normalized_discount).quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)
        if total < 0:
            raise ValueError("Discount cannot exceed the sale subtotal.")
        invoice_number = _generate_invoice_number()
        cursor.execute(
            """
            INSERT INTO sales (invoice_number, customer_id, staff_user_id, subtotal,
                              discount, total, payment_status, sale_status, notes)
            VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s)
            """,
            (
                invoice_number,
                customer_id,
                actor_id,
                subtotal,
                normalized_discount,
                total,
                payment_status,
                sale_status,
                normalized_notes or None,
            ),
        )
        sale_id = int(cursor.lastrowid)
        for row in line_rows:
            cursor.execute(
                """
                INSERT INTO sale_items (sale_id, product_id, quantity, unit_price,
                                       unit_cost, line_discount, line_total)
                VALUES (%s, %s, %s, %s, %s, 0, %s)
                """,
                (
                    sale_id,
                    row["product_id"],
                    row["quantity"],
                    row["unit_price"],
                    row["unit_cost"],
                    row["line_total"],
                ),
            )
            remaining_stock = row["available_stock"] - row["quantity"]
            cursor.execute(
                "UPDATE products SET current_stock = %s WHERE id = %s",
                (remaining_stock, row["product_id"]),
            )
            cursor.execute(
                """
                INSERT INTO inventory_transactions
                    (product_id, performed_by_user_id, transaction_type,
                     quantity_change, stock_after, reference_type, reference_id, notes)
                VALUES (%s, %s, 'sale', %s, %s, 'sale', %s, %s)
                """,
                (
                    row["product_id"],
                    actor_id,
                    -row["quantity"],
                    remaining_stock,
                    sale_id,
                    f"Sale {invoice_number}",
                ),
            )
        connection.commit()
        transaction_started = False
        return sale_id
    except Exception:
        if transaction_started:
            connection.rollback()
        raise
    finally:
        cursor.close()


def get_product_for_update(cursor: Any, product_id: int) -> dict[str, Any]:
    cursor.execute(
        """
        SELECT id, sku, name, cost_price, selling_price, current_stock, is_active
        FROM products WHERE id = %s AND is_active = TRUE FOR UPDATE
        """,
        (product_id,),
    )
    product = cursor.fetchone()
    if product is None:
        raise ValueError("Product not found or inactive.")
    return product
