"""Sales billing and invoice history views."""

from __future__ import annotations

from typing import Any

import pandas as pd
import streamlit as st

from services.catalog_service import list_products
from services.contacts_service import list_customers
from services.sales_service import create_sale, get_sale_detail, list_sales
from utils.documents import build_sale_invoice_pdf
from utils.ui import render_page_header, render_section_heading


def _customer_options(connection: Any, user: dict[str, Any]) -> list[tuple[str, int | None]]:
    choices: list[tuple[str, int | None]] = [("Walk-in customer", None)]
    for customer in list_customers(connection, user["id"], active_only=True):
        choices.append((f"{customer['name']} ({customer['customer_code']})", int(customer["id"])))
    return choices


def render_sales_page(connection: Any, user: dict[str, Any]) -> None:
    render_page_header(
        "Operations",
        "Sales & Billing",
        "Create accurate sales, reduce stock, and keep historical invoice details intact.",
    )

    sales = list_sales(connection, user["id"], limit=50)
    render_section_heading("Recent sales", "Review invoice status and totals for the latest transactions.")
    if sales:
        table = pd.DataFrame(sales)[
            [
                "invoice_number",
                "customer_name",
                "staff_name",
                "payment_status",
                "sale_status",
                "subtotal",
                "discount",
                "total",
                "created_at",
            ]
        ]
        st.dataframe(
            table,
            hide_index=True,
            width="stretch",
            column_config={
                "invoice_number": "Invoice",
                "customer_name": "Customer",
                "staff_name": "Staff",
                "payment_status": "Payment",
                "sale_status": "Sale status",
                "subtotal": st.column_config.NumberColumn("Subtotal", format="$%.2f"),
                "discount": st.column_config.NumberColumn("Discount", format="$%.2f"),
                "total": st.column_config.NumberColumn("Total", format="$%.2f"),
                "created_at": st.column_config.DatetimeColumn("Date"),
            },
        )
    else:
        st.markdown(
            '<div class="nx-empty-state"><h3>No sales yet</h3><p>Completed invoices will appear here once sales are recorded.</p></div>',
            unsafe_allow_html=True,
        )

    render_section_heading("Sales actions", "Create an invoice or inspect and download an existing sale.")
    create_tab, detail_tab = st.tabs(["Create sale", "Invoice detail"])

    with create_tab:
        render_section_heading("Create a sale", "Choose a customer, add products, and record payment status.")
        product_rows = list_products(connection, user["id"], active_only=True)
        if not product_rows:
            st.info("Add at least one active product before creating a sale.")
            return

        with st.form("create_sale_form", clear_on_submit=True):
            customer_label, customer_id = st.selectbox(
                "Customer",
                options=_customer_options(connection, user),
                format_func=lambda option: option[0],
                key="sale_customer_select",
            )
            selected_products = st.multiselect(
                "Products",
                options=[product["id"] for product in product_rows],
                format_func=lambda product_id: next(
                    product["sku"] + " · " + product["name"] for product in product_rows if product["id"] == product_id
                ),
                default=[],
            )
            discount = st.number_input("Discount", min_value=0.0, step=0.01, format="%.2f")
            payment_status = st.selectbox(
                "Payment status",
                options=["unpaid", "partially_paid", "paid", "refunded"],
            )
            sale_status = st.selectbox(
                "Sale status",
                options=["draft", "completed", "voided", "refunded"],
                index=1,
            )
            notes = st.text_area("Notes", max_chars=500)

            line_items: list[dict[str, Any]] = []
            for product_id in selected_products:
                product = next(product for product in product_rows if product["id"] == product_id)
                quantity_col, price_col = st.columns(2)
                quantity = quantity_col.number_input(
                    f"{product['sku']} quantity",
                    min_value=0.001,
                    value=1.0,
                    step=0.001,
                    format="%.3f",
                    key=f"sale_qty_{product_id}",
                )
                unit_price = price_col.number_input(
                    f"{product['sku']} unit price",
                    min_value=0.0,
                    value=float(product["selling_price"]),
                    step=0.01,
                    format="%.2f",
                    key=f"sale_price_{product_id}",
                )
                line_items.append({"product_id": product_id, "quantity": quantity, "unit_price": unit_price})

            submitted = st.form_submit_button("Create sale", type="primary")
        if submitted:
            if not line_items:
                st.error("Select at least one product before creating the sale.")
            else:
                try:
                    sale_id = create_sale(
                        connection,
                        user["id"],
                        customer_id=customer_id,
                        items=line_items,
                        discount=discount,
                        payment_status=payment_status,
                        sale_status=sale_status,
                        notes=notes,
                    )
                    st.success(f"Sale created successfully. Invoice ID: {sale_id}.")
                    st.rerun()
                except ValueError as exc:
                    st.error(str(exc))

    with detail_tab:
        render_section_heading("Invoice detail", "Review line items and download a printable invoice.")
        if not sales:
            st.info("Sales history will appear once invoices are created.")
            return
        sale_choice = st.selectbox(
            "Select invoice",
            options=[sale["id"] for sale in sales],
            format_func=lambda sale_id: next(
                sale["invoice_number"] for sale in sales if sale["id"] == sale_id
            ),
            key="sale_detail_select",
        )
        sale = get_sale_detail(connection, user["id"], sale_choice)
        st.markdown(
            f'<div class="nx-setup-card"><div class="nx-setup-kicker">Invoice {sale["invoice_number"]}</div>'
            f'<h3>{sale["customer_name"] or "Walk-in customer"}</h3>'
            f'<p>Prepared by {sale["staff_name"]} on {sale["created_at"].strftime("%Y-%m-%d %H:%M")}. Payment: {sale["payment_status"]}.</p></div>',
            unsafe_allow_html=True,
        )
        st.dataframe(
            pd.DataFrame(sale["items"])[
                ["sku", "product_name", "quantity", "unit_price", "unit_cost", "line_total"]
            ],
            hide_index=True,
            width="stretch",
            column_config={
                "sku": "SKU",
                "product_name": "Product",
                "quantity": st.column_config.NumberColumn("Qty", format="%.3f"),
                "unit_price": st.column_config.NumberColumn("Unit price", format="$%.2f"),
                "unit_cost": st.column_config.NumberColumn("Unit cost", format="$%.2f"),
                "line_total": st.column_config.NumberColumn("Line total", format="$%.2f"),
            },
        )
        st.markdown(
            f"<div class='nx-order-summary'>Subtotal: ${sale['subtotal']:.2f} &nbsp;·&nbsp; "
            f"Discount: ${sale['discount']:.2f} &nbsp;·&nbsp; Total: ${sale['total']:.2f}</div>",
            unsafe_allow_html=True,
        )
        pdf_bytes = build_sale_invoice_pdf(sale, sale["items"])
        st.download_button(
            "Download invoice PDF",
            data=pdf_bytes,
            file_name=f"{sale['invoice_number']}.pdf",
            mime="application/pdf",
            type="secondary",
        )
