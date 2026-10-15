"""Supplier directory and linked purchase history."""

from __future__ import annotations

from typing import Any

import pandas as pd
import streamlit as st

from services.authorization import ADMIN
from services.contacts_service import (
    list_supplier_history,
    list_suppliers,
    save_supplier,
    set_supplier_active,
)
from utils.ui import render_page_header, render_section_heading


def render_suppliers_page(connection: Any, user: dict[str, Any]) -> None:
    is_admin = user["role"] == ADMIN
    render_page_header(
        "Relationships",
        "Suppliers",
        "Manage supplier contacts and retain purchase references.",
    )
    render_section_heading("Supplier directory", "Search, review, and manage supplier records.")
    filters = st.columns([2, 1])
    with filters[0]:
        search = st.text_input("Search suppliers", placeholder="Name, email, or phone")
    with filters[1]:
        include_inactive = st.checkbox("Include inactive suppliers")
    suppliers = list_suppliers(
        connection,
        user["id"],
        search=search,
        active_only=not include_inactive,
    )
    if suppliers:
        columns = ["supplier_code", "name", "email", "phone", "is_active"]
        if is_admin:
            columns.extend(["purchase_count", "purchase_total"])
        columns.append("created_at")
        display = pd.DataFrame(suppliers)[columns]
        column_config = {
            "supplier_code": "Supplier ID",
            "name": "Name",
            "email": "Email",
            "phone": "Phone",
            "is_active": "Active",
            "created_at": st.column_config.DatetimeColumn("Added"),
        }
        if is_admin:
            column_config.update(
                {
                    "purchase_count": "Purchases",
                    "purchase_total": st.column_config.NumberColumn(
                        "Purchase total", format="$%.2f"
                    ),
                }
            )
        st.dataframe(
            display,
            hide_index=True,
            width="stretch",
            column_config=column_config,
        )
    else:
        st.markdown(
            '<div class="nx-empty-state"><h3>No suppliers found</h3>'
            "<p>Add a supplier or adjust your search to see matching records.</p></div>",
            unsafe_allow_html=True,
        )

    tab_labels = ["Add supplier", "Edit supplier", "Supplier status"]
    if is_admin:
        tab_labels.append("Purchase history")
    render_section_heading("Supplier actions", "Maintain supplier details and review linked purchasing.")
    tabs = st.tabs(tab_labels)
    create_tab, edit_tab, status_tab = tabs[:3]
    with create_tab:
        with st.form("create_supplier_form", clear_on_submit=True):
            name = st.text_input("Name *")
            fields = st.columns(2)
            email = fields[0].text_input("Email")
            phone = fields[1].text_input("Phone")
            address = st.text_area("Address", max_chars=4000)
            submitted = st.form_submit_button("Create supplier", type="primary")
        if submitted:
            try:
                save_supplier(
                    connection,
                    user["id"],
                    name=name,
                    email=email,
                    phone=phone,
                    address=address,
                )
                st.success("Supplier created.")
                st.rerun()
            except ValueError as exc:
                st.error(str(exc))
    with edit_tab:
        if not suppliers:
            st.info("No suppliers match the current filters.")
        else:
            selected = st.selectbox(
                "Supplier to edit",
                suppliers,
                format_func=lambda row: f"{row['name']} · {row['supplier_code']}",
                key="edit_supplier",
            )
            with st.form("edit_supplier_form"):
                name = st.text_input("Name *", value=selected["name"])
                fields = st.columns(2)
                email = fields[0].text_input("Email", value=selected["email"] or "")
                phone = fields[1].text_input("Phone", value=selected["phone"] or "")
                address = st.text_area("Address", value=selected["address"] or "", max_chars=4000)
                submitted = st.form_submit_button("Save supplier changes", type="primary")
            if submitted:
                try:
                    save_supplier(
                        connection,
                        user["id"],
                        name=name,
                        email=email,
                        phone=phone,
                        address=address,
                        supplier_id=selected["id"],
                    )
                    st.success("Supplier details updated.")
                    st.rerun()
                except ValueError as exc:
                    st.error(str(exc))
    with status_tab:
        if not suppliers:
            st.info("No suppliers match the current filters.")
        else:
            selected = st.selectbox(
                "Supplier",
                suppliers,
                format_func=lambda row: f"{row['name']} · {'Active' if row['is_active'] else 'Inactive'}",
                key="status_supplier",
            )
            action = "Reactivate" if not selected["is_active"] else "Deactivate"
            if st.button(f"{action} supplier", key="change_supplier_status"):
                try:
                    set_supplier_active(connection, user["id"], selected["id"], not selected["is_active"])
                    st.success(f"Supplier {action.lower()}d. Historical purchase references are preserved.")
                    st.rerun()
                except ValueError as exc:
                    st.error(str(exc))
    if is_admin:
        with tabs[3]:
            if not suppliers:
                st.info("Purchase history will be available when suppliers are listed.")
            else:
                selected = st.selectbox(
                    "Supplier history",
                    suppliers,
                    format_func=lambda row: row["name"],
                    key="supplier_history",
                )
                history = list_supplier_history(connection, user["id"], selected["id"])
                if history:
                    st.dataframe(
                        pd.DataFrame(history),
                        hide_index=True,
                        width="stretch",
                        column_config={
                            "purchase_number": "Purchase",
                            "created_at": st.column_config.DatetimeColumn("Date"),
                            "total": st.column_config.NumberColumn("Total", format="$%.2f"),
                            "payment_status": "Payment",
                            "receiving_status": "Receiving",
                            "created_by": "Created by",
                        },
                    )
                else:
                    st.info("No purchases have been recorded for this supplier.")
