"""Customer directory and linked sale history."""

from __future__ import annotations

from typing import Any

import pandas as pd
import streamlit as st

from services.contacts_service import (
    list_customer_history,
    list_customers,
    save_customer,
    set_customer_active,
)
from utils.ui import render_page_header, render_section_heading


def render_customers_page(connection: Any, user: dict[str, Any]) -> None:
    render_page_header(
        "Relationships",
        "Customers",
        "Maintain customer records and keep their sales history connected.",
    )
    render_section_heading("Customer directory", "Search, review, and manage customer records.")
    filters = st.columns([2, 1])
    with filters[0]:
        search = st.text_input("Search customers", placeholder="Name, email, or phone")
    with filters[1]:
        include_inactive = st.checkbox("Include inactive customers")
    customers = list_customers(
        connection,
        user["id"],
        search=search,
        active_only=not include_inactive,
    )
    if customers:
        display = pd.DataFrame(customers)[
            [
                "customer_code",
                "name",
                "email",
                "phone",
                "is_active",
                "sale_count",
                "lifetime_sales",
                "created_at",
            ]
        ]
        st.dataframe(
            display,
            hide_index=True,
            width="stretch",
            column_config={
                "customer_code": "Customer ID",
                "name": "Name",
                "email": "Email",
                "phone": "Phone",
                "is_active": "Active",
                "sale_count": "Sales",
                "lifetime_sales": st.column_config.NumberColumn("Lifetime sales", format="$%.2f"),
                "created_at": st.column_config.DatetimeColumn("Added"),
            },
        )
    else:
        st.markdown(
            '<div class="nx-empty-state"><h3>No customers found</h3>'
            "<p>Add a customer or adjust your search to see matching records.</p></div>",
            unsafe_allow_html=True,
        )

    render_section_heading("Customer actions", "Create records, update access status, or review linked sales.")
    create_tab, edit_tab, status_tab, history_tab = st.tabs(
        ["Add customer", "Edit customer", "Customer status", "Sales history"]
    )
    with create_tab:
        with st.form("create_customer_form", clear_on_submit=True):
            name = st.text_input("Name *")
            fields = st.columns(2)
            email = fields[0].text_input("Email")
            phone = fields[1].text_input("Phone")
            address = st.text_area("Address", max_chars=4000)
            submitted = st.form_submit_button("Create customer", type="primary")
        if submitted:
            try:
                save_customer(
                    connection,
                    user["id"],
                    name=name,
                    email=email,
                    phone=phone,
                    address=address,
                )
                st.success("Customer created.")
                st.rerun()
            except ValueError as exc:
                st.error(str(exc))
    with edit_tab:
        if not customers:
            st.info("No customers match the current filters.")
        else:
            selected = st.selectbox(
                "Customer to edit",
                customers,
                format_func=lambda row: f"{row['name']} · {row['customer_code']}",
                key="edit_customer",
            )
            with st.form("edit_customer_form"):
                name = st.text_input("Name *", value=selected["name"])
                fields = st.columns(2)
                email = fields[0].text_input("Email", value=selected["email"] or "")
                phone = fields[1].text_input("Phone", value=selected["phone"] or "")
                address = st.text_area("Address", value=selected["address"] or "", max_chars=4000)
                submitted = st.form_submit_button("Save customer changes", type="primary")
            if submitted:
                try:
                    save_customer(
                        connection,
                        user["id"],
                        name=name,
                        email=email,
                        phone=phone,
                        address=address,
                        customer_id=selected["id"],
                    )
                    st.success("Customer details updated.")
                    st.rerun()
                except ValueError as exc:
                    st.error(str(exc))
    with status_tab:
        if not customers:
            st.info("No customers match the current filters.")
        else:
            selected = st.selectbox(
                "Customer",
                customers,
                format_func=lambda row: f"{row['name']} · {'Active' if row['is_active'] else 'Inactive'}",
                key="status_customer",
            )
            action = "Reactivate" if not selected["is_active"] else "Deactivate"
            if st.button(f"{action} customer", key="change_customer_status"):
                try:
                    set_customer_active(connection, user["id"], selected["id"], not selected["is_active"])
                    st.success(f"Customer {action.lower()}d. Historical sales references are preserved.")
                    st.rerun()
                except ValueError as exc:
                    st.error(str(exc))
    with history_tab:
        if not customers:
            st.info("Sales history will be available when customers are listed.")
        else:
            selected = st.selectbox(
                "Customer history",
                customers,
                format_func=lambda row: row["name"],
                key="customer_history",
            )
            history = list_customer_history(connection, user["id"], selected["id"])
            if history:
                st.dataframe(
                    pd.DataFrame(history),
                    hide_index=True,
                    width="stretch",
                    column_config={
                        "invoice_number": "Invoice",
                        "created_at": st.column_config.DatetimeColumn("Date"),
                        "total": st.column_config.NumberColumn("Total", format="$%.2f"),
                        "payment_status": "Payment",
                        "sale_status": "Sale status",
                        "staff_name": "Staff",
                    },
                )
            else:
                st.info("No sales have been recorded for this customer.")
