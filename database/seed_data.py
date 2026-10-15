"""Insert explicitly marked, idempotent sample records for local demonstrations."""

from __future__ import annotations

import argparse

from database.connection import get_connection

DEMO_CATEGORY = "[DEMO] Office supplies"
DEMO_PRODUCTS = (
    ("DEMO-PEN-001", "[DEMO] Executive pen", "42.00", "89.00", "48.000", "10.000"),
    ("DEMO-NOTE-001", "[DEMO] Linen notebook", "115.00", "199.00", "23.000", "5.000"),
    ("DEMO-DESK-001", "[DEMO] Desk organizer", "260.00", "449.00", "7.000", "3.000"),
)


def seed_demo_data() -> None:
    """Add only demo-labelled category and product rows; never update existing rows."""
    with get_connection() as connection:
        cursor = connection.cursor()
        try:
            connection.start_transaction()
            cursor.execute(
                "INSERT IGNORE INTO categories (name, description) VALUES (%s, %s)",
                (DEMO_CATEGORY, "Clearly marked sample category for local demonstrations."),
            )
            cursor.execute("SELECT id FROM categories WHERE name = %s", (DEMO_CATEGORY,))
            category_row = cursor.fetchone()
            if category_row is None:
                raise RuntimeError("Demo category could not be located after insertion.")
            category_id = category_row[0]
            for sku, name, cost, price, stock, reorder in DEMO_PRODUCTS:
                cursor.execute(
                    """
                    INSERT IGNORE INTO products
                        (sku, name, category_id, cost_price, selling_price, current_stock, reorder_level)
                    VALUES (%s, %s, %s, %s, %s, %s, %s)
                    """,
                    (sku, name, category_id, cost, price, stock, reorder),
                )
            connection.commit()
        except Exception:
            connection.rollback()
            raise
        finally:
            cursor.close()


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--confirm-demo-data",
        action="store_true",
        help="Acknowledge that clearly marked demonstration records will be inserted.",
    )
    arguments = parser.parse_args()
    if not arguments.confirm_demo_data:
        parser.error("Pass --confirm-demo-data to insert DEMO-labelled rows.")
    seed_demo_data()
    print("DEMO category and products inserted (existing rows were not overwritten).")
