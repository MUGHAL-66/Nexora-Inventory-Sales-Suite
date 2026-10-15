"""Purchase entry and history views."""

from __future__ import annotations

from typing import Any

import pandas as pd
import streamlit as st

from services.authorization import ADMIN
from services.catalog_service import list_products
from services.contacts_service import list_suppliers
from services.purchases_service import create_purchase, get_purchase_detail, list_purchases
from utils.ui import render_page_header, render_section_heading


def _supplier_options(connection: Any, user: dict[str, Any]) -> list[tuple[str, int]]:
    choices: list[tuple[str, int]] = []
    for supplier in list_suppliers(connection, user["id"], active_only=True):
        choices.append((f"{supplier['name']} ({supplier['supplier_code']})", int(supplier["id"])))
    return choices


def render_purchases_page(connection: Any, user: dict[str, Any]) -> None:
    is_admin = user["role"] == ADMIN
    render_page_header(
        "Operations",
        "Purchases",
        (
            "Track incoming inventory, costs, and supplier receiving status."
            if is_admin
            else "Record incoming inventory and monitor receiving status."
        ),
    )

    purchases = list_purchases(connection, user["id"], limit=50)
    render_section_heading("Recent purchases", "Review supplier orders and their receiving progress.")
    if purchases:
        columns = [
            "purchase_number",
            "supplier_name",
            "created_by",
            "receiving_status",
            "payment_status",
        ]
        if is_admin:
            columns.extend(["subtotal", "total"])
        columns.append("created_at")
        table = pd.DataFrame(purchases)[columns]
        column_config = {
            "purchase_number": "Purchase",
            "supplier_name": "Supplier",
            "created_by": "Created by",
            "receiving_status": "Receiving",
            "payment_status": "Payment",
            "created_at": st.column_config.DatetimeColumn("Date"),
        }
        if is_admin:
            column_config.update(
                {
                    "subtotal": st.column_config.NumberColumn("Subtotal", format="$%.2f"),
                    "total": st.column_config.NumberColumn("Total", format="$%.2f"),
                }
            )
        st.dataframe(
            table,
            hide_index=True,
            width="stretch",
            column_config=column_config,
        )
    else:
        st.markdown(
            '<div class="nx-empty-state"><h3>No purchases yet</h3><p>Incoming supplier orders will be listed here after they are entered.</p></div>',
            unsafe_allow_html=True,
        )

    render_section_heading("Purchase actions", "Record an incoming order or inspect an existing purchase.")
    create_tab, detail_tab = st.tabs(["Create purchase", "Purchase detail"])

    with create_tab:
        render_section_heading("Create a purchase", "Select a supplier, products, quantities, and receiving status.")
        product_rows = list_products(connection, user["id"], active_only=True)
        supplier_options = _supplier_options(connection, user)
        if not supplier_options:
            st.info("Add at least one active supplier before creating a purchase.")
            return
        if not product_rows:
            st.info("Add at least one active product before recording a purchase.")
            return

        with st.form("create_purchase_form", clear_on_submit=True):
            supplier_id = st.selectbox(
                "Supplier",
                options=[option[1] for option in supplier_options],
                format_func=lambda supplier_id_value: next(
                    label for label, value in supplier_options if value == supplier_id_value
                ),
            )
            selected_products = st.multiselect(
                "Products",
                options=[product["id"] for product in product_rows],
                format_func=lambda product_id: next(
                    product["sku"] + " · " + product["name"] for product in product_rows if product["id"] == product_id
                ),
                default=[],
            )
            receiving_status = st.selectbox(
                "Receiving status",
                options=["ordered", "partially_received", "received", "cancelled"],
                index=2,
            )
            payment_status = st.selectbox(
                "Payment status",
                options=["unpaid", "partially_paid", "paid", "refunded"],
            )
            notes = st.text_area("Notes", max_chars=500)

            line_items: list[dict[str, Any]] = []
            for product_id in selected_products:
                product = next(product for product in product_rows if product["id"] == product_id)
                qty_col, cost_col = st.columns(2)
                ordered = qty_col.number_input(
                    f"{product['sku']} ordered quantity",
                    min_value=0.001,
                    value=1.0,
                    step=0.001,
                    format="%.3f",
                    key=f"purchase_order_qty_{product_id}",
                )
                received = qty_col.number_input(
                    f"{product['sku']} received quantity",
                    min_value=0.0,
                    value=ordered,
                    step=0.001,
                    format="%.3f",
                    key=f"purchase_receive_qty_{product_id}",
                )
                item = {
                    "product_id": product_id,
                    "quantity_ordered": ordered,
                    "quantity_received": received,
                }
                if is_admin:
                    item["unit_cost"] = cost_col.number_input(
                        f"{product['sku']} unit cost",
                        min_value=0.0,
                        value=float(product["cost_price"]),
                        step=0.01,
                        format="%.2f",
                        key=f"purchase_cost_{product_id}",
                    )
                line_items.append(item)

            if not is_admin:
                st.caption("Inventory valuation uses the product’s current catalog cost.")

            submitted = st.form_submit_button("Create purchase", type="primary")
        if submitted:
            if not line_items:
                st.error("Select at least one product before recording the purchase.")
            else:
                try:
                    purchase_id = create_purchase(
                        connection,
                        user["id"],
                        supplier_id=supplier_id,
                        items=line_items,
                        notes=notes,
                        receiving_status=receiving_status,
                        payment_status=payment_status,
                    )
                    st.success(f"Purchase recorded successfully. Purchase ID: {purchase_id}.")
                    st.rerun()
                except ValueError as exc:
                    st.error(str(exc))

    with detail_tab:
        render_section_heading("Purchase detail", "Review ordered and received quantities for a selected purchase.")
        if not purchases:
            st.info("Purchase details will be available once a purchase is recorded.")
            return
        selected_purchase = st.selectbox(
            "Select purchase",
            options=[purchase["id"] for purchase in purchases],
            format_func=lambda purchase_id: next(
                purchase["purchase_number"] for purchase in purchases if purchase["id"] == purchase_id
            ),
            key="purchase_detail_select",
        )
        purchase = get_purchase_detail(connection, user["id"], selected_purchase)
        st.markdown(
            f'<div class="nx-setup-card"><div class="nx-setup-kicker">Purchase {purchase["purchase_number"]}</div>'
            f'<h3>{purchase["supplier_name"]}</h3>'
            f'<p>Created by {purchase["created_by"]} on {purchase["created_at"].strftime("%Y-%m-%d %H:%M")}. Status: {purchase["receiving_status"]}.</p></div>',
            unsafe_allow_html=True,
        )
        detail_columns = ["sku", "product_name", "quantity_ordered", "quantity_received"]
        detail_config = {
            "sku": "SKU",
            "product_name": "Product",
            "quantity_ordered": st.column_config.NumberColumn("Ordered", format="%.3f"),
            "quantity_received": st.column_config.NumberColumn("Received", format="%.3f"),
        }
        if is_admin:
            detail_columns.extend(["unit_cost", "line_total"])
            detail_config.update(
                {
                    "unit_cost": st.column_config.NumberColumn("Unit cost", format="$%.2f"),
                    "line_total": st.column_config.NumberColumn("Line total", format="$%.2f"),
                }
            )
        st.dataframe(
            pd.DataFrame(purchase["items"])[detail_columns],
            hide_index=True,
            width="stretch",
            column_config=detail_config,
        )
        if is_admin:
            st.markdown(
                f"<div class='nx-order-summary'>Subtotal: ${purchase['subtotal']:.2f} "
                f"&nbsp;·&nbsp; Total: ${purchase['total']:.2f}</div>",
                unsafe_allow_html=True,
            )
