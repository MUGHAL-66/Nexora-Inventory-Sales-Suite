"""Live, role-checked dashboard queries."""

from __future__ import annotations

from datetime import date, timedelta
from typing import Any

from services.authorization import (
    ADMIN_FINANCIALS,
    DASHBOARD_ACCESS,
    SALES_FINANCIALS,
    require_permission,
    role_has_permission,
)


def get_dashboard_data(
    connection: Any,
    actor_id: int,
    start_date: date,
    end_date: date,
) -> dict[str, Any]:
    """Return actual database metrics and chart/table rows for an inclusive date range."""
    actor = require_permission(connection, actor_id, DASHBOARD_ACCESS)
    can_view_sales_financials = role_has_permission(actor["role"], SALES_FINANCIALS)
    can_view_admin_financials = role_has_permission(actor["role"], ADMIN_FINANCIALS)
    if not isinstance(start_date, date) or not isinstance(end_date, date):
        raise ValueError("Choose a valid start and end date.")
    if end_date < start_date:
        raise ValueError("End date must be on or after the start date.")
    if (end_date - start_date).days > 3660:
        raise ValueError("Choose a date range of ten years or less.")
    exclusive_end = end_date + timedelta(days=1)
    cursor = connection.cursor(dictionary=True)
    try:
        sales_total_select = (
            """
                (SELECT COALESCE(SUM(total), 0) FROM sales
                 WHERE sale_status = 'completed' AND created_at >= %s AND created_at < %s)
                    AS sales_total,
            """
            if can_view_sales_financials
            else ""
        )
        summary_parameters = (
            (start_date, exclusive_end) if can_view_sales_financials else ()
        ) + (start_date, exclusive_end)
        cursor.execute(
            f"""
            SELECT
                (SELECT COUNT(*) FROM products WHERE is_active = TRUE) AS product_count,
                (SELECT COUNT(*) FROM customers WHERE is_active = TRUE) AS customer_count,
                (SELECT COUNT(*) FROM products
                 WHERE is_active = TRUE AND current_stock <= reorder_level) AS low_stock_count,
                {sales_total_select}
                (SELECT COUNT(*) FROM sales
                 WHERE sale_status = 'completed' AND created_at >= %s AND created_at < %s)
                    AS sales_count
            """,
            summary_parameters,
        )
        metrics = cursor.fetchone()
        if metrics is None:
            raise RuntimeError("Dashboard summary query returned no result.")
        if not can_view_sales_financials:
            metrics.pop("sales_total", None)
        if can_view_admin_financials:
            cursor.execute(
                """
                SELECT COALESCE(SUM(total), 0) AS purchase_total
                FROM purchases
                WHERE receiving_status <> 'cancelled'
                  AND created_at >= %s AND created_at < %s
                """,
                (start_date, exclusive_end),
            )
            purchases = cursor.fetchone()
            if purchases is None:
                raise RuntimeError("Dashboard purchase summary query returned no result.")
            metrics["purchase_total"] = purchases["purchase_total"]
            cursor.execute(
                """
                SELECT
                    COUNT(DISTINCT s.id) AS sales_count,
                    COUNT(DISTINCT costs.sale_id) AS costed_sales,
                    SUM(s.total - costs.cost_total) AS gross_profit
                FROM sales s
                LEFT JOIN (
                    SELECT sale_id, SUM(quantity * unit_cost) AS cost_total
                    FROM sale_items GROUP BY sale_id
                ) costs ON costs.sale_id = s.id
                WHERE s.sale_status = 'completed'
                  AND s.created_at >= %s AND s.created_at < %s
                """,
                (start_date, exclusive_end),
            )
            profit = cursor.fetchone()
            if profit["sales_count"] == 0 or profit["sales_count"] != profit["costed_sales"]:
                metrics["gross_profit"] = None
            else:
                metrics["gross_profit"] = profit["gross_profit"]

        trend_total_select = "SUM(total) AS sales_total," if can_view_sales_financials else ""
        cursor.execute(
            f"""
            SELECT DATE(created_at) AS day, {trend_total_select} COUNT(*) AS sale_count
            FROM sales
            WHERE sale_status = 'completed' AND created_at >= %s AND created_at < %s
            GROUP BY DATE(created_at) ORDER BY day
            """,
            (start_date, exclusive_end),
        )
        sales_trend = list(cursor.fetchall())

        top_product_total_select = (
            ", SUM(si.line_total) AS sales_total" if can_view_sales_financials else ""
        )
        cursor.execute(
            f"""
            SELECT p.id AS product_id, p.sku, p.name,
                   SUM(si.quantity) AS units_sold{top_product_total_select}
            FROM sale_items si
            JOIN sales s ON s.id = si.sale_id
            JOIN products p ON p.id = si.product_id
            WHERE s.sale_status = 'completed' AND s.created_at >= %s AND s.created_at < %s
            GROUP BY p.id, p.sku, p.name
            ORDER BY units_sold DESC, p.name
            LIMIT 10
            """,
            (start_date, exclusive_end),
        )
        top_products = list(cursor.fetchall())

        if can_view_admin_financials:
            cursor.execute(
                """
                SELECT transaction_type, reference_number, counterparty, amount, status, created_at
                FROM (
                    SELECT 'Sale' AS transaction_type, s.invoice_number AS reference_number,
                           COALESCE(c.name, 'Walk-in customer') AS counterparty,
                           s.total AS amount, s.payment_status AS status, s.created_at
                    FROM sales s LEFT JOIN customers c ON c.id = s.customer_id
                    WHERE s.created_at >= %s AND s.created_at < %s
                    UNION ALL
                    SELECT 'Purchase' AS transaction_type, p.purchase_number AS reference_number,
                           sp.name AS counterparty, p.total AS amount, p.receiving_status AS status,
                           p.created_at
                    FROM purchases p JOIN suppliers sp ON sp.id = p.supplier_id
                    WHERE p.created_at >= %s AND p.created_at < %s
                ) recent
                ORDER BY created_at DESC
                LIMIT 12
                """,
                (start_date, exclusive_end, start_date, exclusive_end),
            )
        else:
            amount_select = "s.total AS amount," if can_view_sales_financials else ""
            cursor.execute(
                f"""
                SELECT 'Sale' AS transaction_type, s.invoice_number AS reference_number,
                       COALESCE(c.name, 'Walk-in customer') AS counterparty,
                       {amount_select} s.payment_status AS status, s.created_at
                FROM sales s LEFT JOIN customers c ON c.id = s.customer_id
                WHERE s.created_at >= %s AND s.created_at < %s
                ORDER BY s.created_at DESC, s.id DESC LIMIT 12
                """,
                (start_date, exclusive_end),
            )
        recent_transactions = list(cursor.fetchall())

        cursor.execute(
            """
            SELECT id, sku, name, current_stock, reorder_level
            FROM products
            WHERE is_active = TRUE AND current_stock <= reorder_level
            ORDER BY (reorder_level - current_stock) DESC, name
            LIMIT 12
            """
        )
        low_stock_products = list(cursor.fetchall())
        return {
            "metrics": metrics,
            "sales_trend": sales_trend,
            "top_products": top_products,
            "recent_transactions": recent_transactions,
            "low_stock_products": low_stock_products,
        }
    finally:
        cursor.close()
