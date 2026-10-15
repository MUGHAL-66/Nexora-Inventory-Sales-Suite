"""Audited stock adjustment and history views."""

from __future__ import annotations

from typing import Any

import pandas as pd
import streamlit as st

from services.authorization import ADMIN
from services.catalog_service import adjust_stock, list_products, list_stock_transactions
from utils.ui import render_page_header, render_section_heading


def render_inventory_page(connection: Any, user: dict[str, Any]) -> None:
    is_admin = user["role"] == ADMIN
    render_page_header(
        "Operations",
        "Inventory & Stock History",
        "Record reasoned stock adjustments and review the movement audit trail.",
    )
    products = list_products(connection, user["id"], active_only=False)
    render_section_heading("Inventory workspace", "Adjust stock or inspect the recorded movement history.")
    tabs = st.tabs(["Adjust stock", "Stock history"] if is_admin else ["Stock history"])
    if is_admin:
        with tabs[0]:
            active_products = [product for product in products if product["is_active"]]
            if not active_products:
                st.info("Add and activate a product before recording a stock adjustment.")
            else:
                with st.form("stock_adjustment_form", clear_on_submit=True):
                    selected = st.selectbox(
                        "Product",
                        active_products,
                        format_func=lambda item: f"{item['sku']} · {item['name']} (on hand: {item['current_stock']})",
                    )
                    quantity_change = st.number_input(
                        "Quantity change",
                        min_value=-1_000_000_000.0,
                        max_value=1_000_000_000.0,
                        value=0.0,
                        step=1.0,
                        format="%.3f",
                        help="Use a positive number to add stock or a negative number to remove stock.",
                    )
                    reason = st.text_input("Adjustment reason *", max_chars=500)
                    submitted = st.form_submit_button("Record adjustment", type="primary")
                if submitted:
                    try:
                        new_stock = adjust_stock(
                            connection,
                            user["id"],
                            product_id=selected["id"],
                            quantity_change=quantity_change,
                            notes=reason,
                        )
                        st.success(f"Stock adjusted. New on-hand quantity: {new_stock}.")
                        st.rerun()
                    except ValueError as exc:
                        st.error(str(exc))
    with tabs[1] if is_admin else tabs[0]:
        history = list_stock_transactions(connection, user["id"], limit=250)
        if history:
            display = pd.DataFrame(history)[
                [
                    "sku",
                    "product_name",
                    "transaction_type",
                    "quantity_change",
                    "stock_after",
                    "reference_type",
                    "notes",
                    "created_at",
                    "performed_by",
                ]
            ]
            st.dataframe(
                display,
                hide_index=True,
                width="stretch",
                column_config={
                    "sku": "SKU",
                    "product_name": "Product",
                    "transaction_type": "Movement",
                    "quantity_change": st.column_config.NumberColumn("Change", format="%.3f"),
                    "stock_after": st.column_config.NumberColumn("On hand after", format="%.3f"),
                    "reference_type": "Reference",
                    "notes": "Reason",
                    "created_at": st.column_config.DatetimeColumn("Recorded"),
                    "performed_by": "Recorded by",
                },
            )
        else:
            st.markdown(
                '<div class="nx-empty-state"><h3>No stock movements yet</h3>'
                "<p>Each adjustment will be retained here with its quantity, resulting balance, and reason.</p></div>",
                unsafe_allow_html=True,
            )
