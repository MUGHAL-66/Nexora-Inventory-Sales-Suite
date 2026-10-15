"""Nexora Inventory & Sales Suite entry point."""

from __future__ import annotations

import logging
from collections import defaultdict
from collections.abc import Callable
from typing import Any

import streamlit as st
from mysql.connector import Error as MySQLError

from database.connection import DatabaseConfigurationError, get_connection
from pages.customers import render_customers_page
from pages.dashboard import render_dashboard
from pages.inventory import render_inventory_page
from pages.login import render_login
from pages.products import render_products_page
from pages.purchases import render_purchases_page
from pages.sales import render_sales_page
from pages.suppliers import render_suppliers_page
from pages.users import render_users_page
from services.auth_service import get_active_user
from services.authorization import AuthorizationError, role_can_access_page
from services.navigation import NAV_ITEMS, render_sidebar
from utils.ui import apply_theme

logging.basicConfig(level=logging.INFO)
LOGGER = logging.getLogger(__name__)

st.set_page_config(
    page_title="Nexora | Inventory & Sales Suite",
    page_icon="N",
    layout="wide",
    initial_sidebar_state="expanded",
)

_PAGE_RENDERERS: dict[str, Callable[..., None]] = {
    "dashboard": render_dashboard,
    "products": render_products_page,
    "customers": render_customers_page,
    "suppliers": render_suppliers_page,
    "inventory": render_inventory_page,
    "sales": render_sales_page,
    "purchases": render_purchases_page,
    "users": render_users_page,
}
_PAGE_OBJECTS: dict[str, Any] = {}


def _render_route(route_key: str) -> None:
    """Authenticate, authorize, and render one registered application route."""
    apply_theme()
    try:
        with get_connection() as connection:
            user_id = st.session_state.get("authenticated_user_id")
            if user_id is None:
                if route_key != "login":
                    st.switch_page(_PAGE_OBJECTS["login"])
                render_login(connection)
                return

            user = get_active_user(connection, user_id)
            if user is None:
                st.session_state.pop("authenticated_user_id", None)
                st.switch_page(_PAGE_OBJECTS["login"])

            if route_key == "login":
                st.switch_page(_PAGE_OBJECTS["dashboard"])

            if route_key not in _PAGE_RENDERERS:
                raise RuntimeError(f"Unregistered application route: {route_key}")

            if not role_can_access_page(user["role"], route_key):
                st.error("You do not have permission to access that page.")
                st.page_link(
                    _PAGE_OBJECTS["dashboard"],
                    label="Return to Dashboard",
                    icon=":material/dashboard:",
                )
                return

            render_sidebar(user, _PAGE_OBJECTS)
            if route_key == "dashboard":
                _PAGE_RENDERERS[route_key](
                    connection,
                    user,
                    _PAGE_OBJECTS["products"],
                )
            else:
                _PAGE_RENDERERS[route_key](connection, user)
    except DatabaseConfigurationError:
        st.warning(
            "Database not configured. Copy `.env.example` to `.env`, set the MySQL connection "
            "values, and follow the setup steps in README.md."
        )
    except AuthorizationError:
        st.session_state.pop("authenticated_user_id", None)
        st.warning("Your session permissions changed. Please sign in again.")
        if route_key != "login":
            st.switch_page(_PAGE_OBJECTS["login"])
    except MySQLError:
        LOGGER.exception("Unable to access the configured inventory database.")
        st.error(
            "The inventory database is currently unavailable. Check the server-side logs and "
            "database setup, then try again."
        )


def _make_page_runner(route_key: str) -> Callable[[], None]:
    def run_page() -> None:
        _render_route(route_key)

    run_page.__name__ = f"render_{route_key}_route"
    return run_page


for _item in NAV_ITEMS:
    _PAGE_OBJECTS[_item["key"]] = st.Page(
        _make_page_runner(_item["key"]),
        title=_item["label"],
        icon=_item["icon"],
        url_path=_item["key"],
    )
_PAGE_OBJECTS["login"] = st.Page(
    _make_page_runner("login"),
    title="Sign in",
    icon=":material/lock:",
    url_path="login",
    default=True,
)

_page_sections: dict[str, list[Any]] = defaultdict(list)
for _item in NAV_ITEMS:
    _page_sections[_item["group"]].append(_PAGE_OBJECTS[_item["key"]])
_page_sections["AUTHENTICATION"].append(_PAGE_OBJECTS["login"])

# The supported hidden position disables Streamlit's auto-generated navigation;
# the branded sidebar links to these same registered Page objects.
_selected_page = st.navigation(_page_sections, position="hidden")
_selected_page.run()
