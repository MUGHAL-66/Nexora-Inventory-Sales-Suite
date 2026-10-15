"""Database-backed catalog operations and auditable stock adjustments."""

from __future__ import annotations

from decimal import Decimal, InvalidOperation
from typing import Any

from mysql.connector.errors import IntegrityError

from services.authorization import (
    ADMIN,
    require_admin,
    require_catalog_read,
    require_inventory_access,
)
from utils.validators import (
    validate_nonnegative_amount,
    validate_optional_text,
    validate_required_text,
    validate_sku,
)


def _money(value: Any, field: str) -> Decimal:
    amount = validate_nonnegative_amount(value)
    if amount.as_tuple().exponent < -2:
        raise ValueError(f"{field} may have at most two decimal places.")
    if amount > Decimal("99999999999.99"):
        raise ValueError(f"{field} exceeds the supported maximum.")
    return amount


def _stock(value: Any, field: str) -> Decimal:
    amount = validate_nonnegative_amount(value)
    if amount.as_tuple().exponent < -3 or amount > Decimal("9999999999.999"):
        raise ValueError(f"{field} must be non-negative with at most three decimal places.")
    return amount


def list_categories(connection: Any, actor_id: int, *, active_only: bool = False) -> list[dict[str, Any]]:
    require_catalog_read(connection, actor_id)
    cursor = connection.cursor(dictionary=True)
    try:
        sql = """
            SELECT c.id, c.name, c.description, c.is_active, c.created_at,
                   COUNT(p.id) AS product_count
            FROM categories c LEFT JOIN products p ON p.category_id = c.id
        """
        if active_only:
            sql += " WHERE c.is_active = TRUE"
        sql += " GROUP BY c.id ORDER BY c.name"
        cursor.execute(sql)
        return list(cursor.fetchall())
    finally:
        cursor.close()


def save_category(
    connection: Any,
    actor_id: int,
    *,
    name: str,
    description: str = "",
    category_id: int | None = None,
) -> int:
    require_admin(connection, actor_id)
    name = validate_required_text(name, "Category name", 120)
    description = validate_optional_text(description, "Description", 4000)
    cursor = connection.cursor()
    try:
        if category_id is None:
            cursor.execute(
                "INSERT INTO categories (name, description) VALUES (%s, %s)",
                (name, description),
            )
            category_id = int(cursor.lastrowid)
        else:
            cursor.execute("SELECT id FROM categories WHERE id = %s", (category_id,))
            if cursor.fetchone() is None:
                raise ValueError("Category not found.")
            cursor.execute(
                "UPDATE categories SET name = %s, description = %s WHERE id = %s",
                (name, description, category_id),
            )
        connection.commit()
        return category_id
    except IntegrityError as exc:
        connection.rollback()
        if exc.errno == 1062:
            raise ValueError("A category with that name already exists.") from exc
        raise
    finally:
        cursor.close()


def set_category_active(connection: Any, actor_id: int, category_id: int, active: bool) -> None:
    require_admin(connection, actor_id)
    cursor = connection.cursor()
    try:
        cursor.execute("UPDATE categories SET is_active = %s WHERE id = %s", (active, category_id))
        if cursor.rowcount == 0:
            raise ValueError("Category not found or already has that status.")
        connection.commit()
    finally:
        cursor.close()


def list_products(
    connection: Any,
    actor_id: int,
    *,
    search: str = "",
    category_id: int | None = None,
    active_only: bool = True,
) -> list[dict[str, Any]]:
    actor = require_catalog_read(connection, actor_id)
    cost_column = "p.cost_price" if actor["role"] == ADMIN else "NULL AS cost_price"
    filters: list[str] = []
    parameters: list[Any] = []
    if active_only:
        filters.append("p.is_active = TRUE")
    normalized = search.strip()
    if normalized:
        filters.append("(p.sku LIKE %s OR p.name LIKE %s)")
        wildcard = f"%{normalized}%"
        parameters.extend((wildcard, wildcard))
    if category_id is not None:
        filters.append("p.category_id = %s")
        parameters.append(category_id)
    where = " WHERE " + " AND ".join(filters) if filters else ""
    cursor = connection.cursor(dictionary=True)
    try:
        cursor.execute(
            """
            SELECT p.id, p.sku, p.name, p.category_id, c.name AS category_name,
                   p.description, """
            + cost_column
            + """, p.selling_price, p.current_stock,
                   p.reorder_level, p.is_active, p.created_at, p.updated_at
            FROM products p LEFT JOIN categories c ON c.id = p.category_id
            """
            + where
            + " ORDER BY p.name, p.id",
            tuple(parameters),
        )
        return list(cursor.fetchall())
    finally:
        cursor.close()


def save_product(
    connection: Any,
    actor_id: int,
    *,
    sku: str,
    name: str,
    category_id: int | None,
    description: str,
    cost_price: Any,
    selling_price: Any,
    reorder_level: Any,
    product_id: int | None = None,
) -> int:
    """Create/update catalog data without ever writing current_stock."""
    require_admin(connection, actor_id)
    sku = validate_sku(sku)
    name = validate_required_text(name, "Product name", 180)
    description = validate_optional_text(description, "Description", 4000)
    cost = _money(cost_price, "Cost price")
    price = _money(selling_price, "Selling price")
    reorder = _stock(reorder_level, "Reorder level")
    cursor = connection.cursor()
    try:
        if category_id is not None:
            cursor.execute(
                """
                SELECT c.id
                FROM categories c
                WHERE c.id = %s
                  AND (
                      c.is_active = TRUE
                      OR EXISTS (
                          SELECT 1 FROM products p
                          WHERE p.id = %s AND p.category_id = c.id
                      )
                  )
                """,
                (category_id, product_id),
            )
            if cursor.fetchone() is None:
                raise ValueError("Choose an active category or leave the category blank.")
        if product_id is None:
            cursor.execute(
                """
                INSERT INTO products
                    (sku, name, category_id, description, cost_price, selling_price,
                     current_stock, reorder_level)
                VALUES (%s, %s, %s, %s, %s, %s, 0, %s)
                """,
                (sku, name, category_id, description, cost, price, reorder),
            )
            product_id = int(cursor.lastrowid)
        else:
            cursor.execute("SELECT id FROM products WHERE id = %s", (product_id,))
            if cursor.fetchone() is None:
                raise ValueError("Product not found.")
            cursor.execute(
                """
                UPDATE products
                SET sku = %s, name = %s, category_id = %s, description = %s,
                    cost_price = %s, selling_price = %s, reorder_level = %s
                WHERE id = %s
                """,
                (sku, name, category_id, description, cost, price, reorder, product_id),
            )
        connection.commit()
        return product_id
    except IntegrityError as exc:
        connection.rollback()
        if exc.errno == 1062:
            raise ValueError("That SKU is already in use.") from exc
        raise
    finally:
        cursor.close()


def set_product_active(connection: Any, actor_id: int, product_id: int, active: bool) -> None:
    """Deactivate/reactivate products without deleting historical references."""
    require_admin(connection, actor_id)
    cursor = connection.cursor()
    try:
        cursor.execute("UPDATE products SET is_active = %s WHERE id = %s", (active, product_id))
        if cursor.rowcount == 0:
            raise ValueError("Product not found or already has that status.")
        connection.commit()
    finally:
        cursor.close()


def adjust_stock(
    connection: Any,
    actor_id: int,
    *,
    product_id: int,
    quantity_change: Any,
    notes: str,
) -> Decimal:
    """Apply an admin stock adjustment and append its auditable transaction."""
    actor = require_admin(connection, actor_id)
    try:
        change = Decimal(str(quantity_change))
    except (InvalidOperation, ValueError) as exc:
        raise ValueError("Stock adjustment must be numeric.") from exc
    if not change.is_finite() or change == 0:
        raise ValueError("Stock adjustment must be a non-zero quantity.")
    if abs(change) > Decimal("9999999999.999") or change.as_tuple().exponent < -3:
        raise ValueError("Stock adjustment must have at most three decimal places.")
    notes = validate_required_text(notes, "Adjustment reason", 500)
    cursor = connection.cursor(dictionary=True)
    try:
        connection.start_transaction()
        cursor.execute(
            "SELECT current_stock FROM products WHERE id = %s AND is_active = TRUE FOR UPDATE",
            (product_id,),
        )
        product = cursor.fetchone()
        if product is None:
            raise ValueError("Active product not found.")
        new_stock = product["current_stock"] + change
        if new_stock < 0:
            raise ValueError("Stock cannot be reduced below zero.")
        cursor.execute(
            "UPDATE products SET current_stock = %s WHERE id = %s",
            (new_stock, product_id),
        )
        cursor.execute(
            """
            INSERT INTO inventory_transactions
                (product_id, performed_by_user_id, transaction_type,
                 quantity_change, stock_after, reference_type, notes)
            VALUES (%s, %s, %s, %s, %s, 'adjustment', %s)
            """,
            (
                product_id,
                actor["id"],
                "adjustment_in" if change > 0 else "adjustment_out",
                change,
                new_stock,
                notes,
            ),
        )
        connection.commit()
        return new_stock
    except Exception:
        connection.rollback()
        raise
    finally:
        cursor.close()


def list_stock_transactions(
    connection: Any, actor_id: int, *, product_id: int | None = None, limit: int = 100
) -> list[dict[str, Any]]:
    require_inventory_access(connection, actor_id)
    if not 1 <= limit <= 500:
        raise ValueError("Transaction limit must be between 1 and 500.")
    cursor = connection.cursor(dictionary=True)
    try:
        if product_id is None:
            cursor.execute(
                """
                SELECT t.id, p.sku, p.name AS product_name, t.transaction_type,
                       t.quantity_change, t.stock_after, t.reference_type, t.notes,
                       t.created_at, u.full_name AS performed_by
                FROM inventory_transactions t JOIN products p ON p.id = t.product_id
                LEFT JOIN users u ON u.id = t.performed_by_user_id
                ORDER BY t.created_at DESC, t.id DESC LIMIT %s
                """,
                (limit,),
            )
        else:
            cursor.execute(
                """
                SELECT t.id, p.sku, p.name AS product_name, t.transaction_type,
                       t.quantity_change, t.stock_after, t.reference_type, t.notes,
                       t.created_at, u.full_name AS performed_by
                FROM inventory_transactions t JOIN products p ON p.id = t.product_id
                LEFT JOIN users u ON u.id = t.performed_by_user_id
                WHERE t.product_id = %s
                ORDER BY t.created_at DESC, t.id DESC LIMIT %s
                """,
                (product_id, limit),
            )
        return list(cursor.fetchall())
    finally:
        cursor.close()
