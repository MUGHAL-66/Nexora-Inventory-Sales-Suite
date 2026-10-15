"""Shared application navigation."""

from __future__ import annotations

from html import escape
from typing import Any

import streamlit as st

from services.authorization import (
    CATALOG_READ,
    CUSTOMER_ACCESS,
    DASHBOARD_ACCESS,
    INVENTORY_ACCESS,
    PURCHASE_ACCESS,
    SALES_ACCESS,
    SUPPLIER_ACCESS,
    USER_ADMINISTRATION,
    USER_ROLE_LABELS,
    role_can_access_page,
)

NAV_ITEMS = (
    {
        "key": "dashboard",
        "label": "Dashboard",
        "icon": ":material/dashboard:",
        "group": "OVERVIEW",
        "permission": DASHBOARD_ACCESS,
    },
    {
        "key": "products",
        "label": "Products",
        "icon": ":material/inventory_2:",
        "group": "CATALOG",
        "permission": CATALOG_READ,
    },
    {
        "key": "customers",
        "label": "Customers",
        "icon": ":material/group:",
        "group": "RELATIONSHIPS",
        "permission": CUSTOMER_ACCESS,
    },
    {
        "key": "suppliers",
        "label": "Suppliers",
        "icon": ":material/local_shipping:",
        "group": "RELATIONSHIPS",
        "permission": SUPPLIER_ACCESS,
    },
    {
        "key": "inventory",
        "label": "Inventory",
        "icon": ":material/warehouse:",
        "group": "OPERATIONS",
        "permission": INVENTORY_ACCESS,
    },
    {
        "key": "sales",
        "label": "Sales",
        "icon": ":material/point_of_sale:",
        "group": "OPERATIONS",
        "permission": SALES_ACCESS,
    },
    {
        "key": "purchases",
        "label": "Purchases",
        "icon": ":material/shopping_bag:",
        "group": "OPERATIONS",
        "permission": PURCHASE_ACCESS,
    },
    {
        "key": "users",
        "label": "Users",
        "icon": ":material/manage_accounts:",
        "group": "ADMINISTRATION",
        "permission": USER_ADMINISTRATION,
    },
)


def navigation_items_for_role(role: str) -> tuple[dict[str, Any], ...]:
    """Return only the navigation entries available to a user's role."""
    return tuple(item for item in NAV_ITEMS if role_can_access_page(role, item["key"]))


def render_sidebar(user: dict[str, Any], pages: dict[str, Any]) -> None:
    """Render the branded sidebar with links to registered Streamlit pages."""
    with st.sidebar:
        st.markdown(
            '<div class="nx-brand"><div class="nx-brand-mark">N</div><div>'
            '<div class="nx-brand-name">nexora<span>.</span></div>'
            '<div class="nx-brand-caption">INVENTORY &amp; SALES SUITE</div>'
            "</div></div>",
            unsafe_allow_html=True,
        )

        current_group = None
        for item in navigation_items_for_role(user["role"]):
            if item["group"] != current_group:
                current_group = item["group"]
                st.markdown(
                    f'<div class="nx-nav-group">{current_group}</div>',
                    unsafe_allow_html=True,
                )
            st.page_link(
                pages[item["key"]],
                label=item["label"],
                icon=item["icon"],
                width="stretch",
            )

        st.markdown(
            '<div class="nx-sidebar-footer"><div class="nx-status-dot"></div>'
            f'<div><strong>{escape(user["full_name"])}</strong>'
            f'<span>{escape(USER_ROLE_LABELS[user["role"]])}</span></div></div>',
            unsafe_allow_html=True,
        )
        if st.button("Log out", key="logout", width="stretch"):
            st.session_state.pop("authenticated_user_id", None)
            st.rerun()
