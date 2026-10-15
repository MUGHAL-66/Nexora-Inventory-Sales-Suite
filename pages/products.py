"""Product and category management views."""

from __future__ import annotations

from collections.abc import Callable
from typing import Any

import pandas as pd
import streamlit as st

from services.authorization import ADMIN
from services.catalog_service import (
    list_categories,
    list_products,
    save_category,
    save_product,
    set_category_active,
    set_product_active,
)
from utils.ui import render_page_header, render_section_heading


def _show_validation_error(action: Callable[[], object]) -> bool:
    try:
        action()
        return True
    except ValueError as exc:
        st.error(str(exc))
        return False


def render_products_page(connection: Any, user: dict[str, Any]) -> None:
    render_page_header(
        "Catalog",
        "Products & Categories",
        "Keep your catalog accurate and easy to manage.",
    )
    render_section_heading("Product catalog", "Search, filter, and review stock and pricing.")
    admin = user["role"] == ADMIN
    category_rows = list_categories(
        connection,
        user["id"],
        active_only=user["role"] != ADMIN,
    )
    active_categories = [row for row in category_rows if row["is_active"]]

    filter_cols = st.columns([1.6, 1, 1])
    with filter_cols[0]:
        search = st.text_input("Search catalog", placeholder="Product name or SKU")
    with filter_cols[1]:
        category_filter = st.selectbox(
            "Category filter",
            options=[None, *[row["id"] for row in active_categories]],
            format_func=lambda value: "All categories" if value is None else next(
                row["name"] for row in active_categories if row["id"] == value
            ),
        )
    with filter_cols[2]:
        include_inactive = st.checkbox("Include inactive", value=False, disabled=not admin)

    products = list_products(
        connection,
        user["id"],
        search=search,
        category_id=category_filter,
        active_only=not (admin and include_inactive),
    )
    if products:
        product_frame = pd.DataFrame(products)
        product_frame = product_frame.rename(
            columns={
                "sku": "SKU",
                "name": "Product",
                "category_name": "Category",
                "cost_price": "Cost",
                "selling_price": "Price",
                "current_stock": "On hand",
                "reorder_level": "Reorder at",
                "is_active": "Active",
            }
        )
        visible_columns = ["SKU", "Product", "Category", "Price", "On hand", "Reorder at", "Active"]
        if admin:
            visible_columns.insert(3, "Cost")
        st.dataframe(
            product_frame[visible_columns],
            hide_index=True,
            width="stretch",
            column_config={
                "Cost": st.column_config.NumberColumn(format="$%.2f"),
                "Price": st.column_config.NumberColumn(format="$%.2f"),
                "On hand": st.column_config.NumberColumn(format="%.3f"),
                "Reorder at": st.column_config.NumberColumn(format="%.3f"),
            },
        )
    else:
        st.markdown(
            '<div class="nx-empty-state"><h3>No products found</h3>'
            "<p>Try changing your search or add the first product.</p></div>",
            unsafe_allow_html=True,
        )

    if not admin:
        st.info("Sales Staff can view the active product catalog. Product and category changes require an administrator.")
        return

    render_section_heading("Catalog actions", "Create and maintain products and product categories.")
    product_tab, category_tab = st.tabs(["Products", "Categories"])
    with product_tab:
        create_tab, edit_tab, status_tab = st.tabs(["Add product", "Edit product", "Product status"])
        with create_tab:
            with st.form("create_product_form", clear_on_submit=True):
                fields = st.columns(2)
                sku = fields[0].text_input("SKU *")
                name = fields[1].text_input("Product name *")
                category_options = [None, *[row["id"] for row in active_categories]]
                category_id = st.selectbox(
                    "Category",
                    options=category_options,
                    format_func=lambda value: "Uncategorized" if value is None else next(
                        row["name"] for row in active_categories if row["id"] == value
                    ),
                    key="new_product_category",
                )
                description = st.text_area("Description", max_chars=4000)
                price_cols = st.columns(3)
                cost = price_cols[0].number_input("Cost price", min_value=0.0, step=1.0, format="%.2f")
                price = price_cols[1].number_input("Selling price", min_value=0.0, step=1.0, format="%.2f")
                reorder = price_cols[2].number_input("Reorder level", min_value=0.0, step=1.0, format="%.3f")
                st.caption("New products start at zero stock. Use Inventory & Stock History for audited quantity adjustments.")
                submitted = st.form_submit_button("Create product", type="primary")
            if submitted:
                if _show_validation_error(
                    lambda: save_product(
                        connection,
                        user["id"],
                        sku=sku,
                        name=name,
                        category_id=category_id,
                        description=description,
                        cost_price=cost,
                        selling_price=price,
                        reorder_level=reorder,
                    )
                ):
                    st.success("Product created with zero stock.")
                    st.rerun()
        with edit_tab:
            all_products = list_products(connection, user["id"], active_only=False)
            if not all_products:
                st.info("Add a product before editing.")
            else:
                selected_product = st.selectbox(
                    "Product to edit",
                    options=all_products,
                    format_func=lambda item: f"{item['sku']} · {item['name']}",
                    key="edit_product_selection",
                )
                categories_by_id = {item["id"]: item for item in category_rows}
                category_options = [None, *[item["id"] for item in active_categories]]
                if (
                    selected_product["category_id"] is not None
                    and selected_product["category_id"] not in category_options
                ):
                    category_options.append(selected_product["category_id"])
                with st.form("edit_product_form"):
                    fields = st.columns(2)
                    sku = fields[0].text_input("SKU *", value=selected_product["sku"])
                    name = fields[1].text_input("Product name *", value=selected_product["name"])
                    current_category = selected_product["category_id"]
                    category_id = st.selectbox(
                        "Category",
                        options=category_options,
                        index=category_options.index(current_category),
                        format_func=lambda value: "Uncategorized" if value is None else categories_by_id[value]["name"],
                        key=f"edit_product_category_{selected_product['id']}",
                    )
                    description = st.text_area(
                        "Description",
                        value=selected_product["description"] or "",
                        max_chars=4000,
                    )
                    price_cols = st.columns(3)
                    cost = price_cols[0].number_input(
                        "Cost price", min_value=0.0, value=float(selected_product["cost_price"]), step=1.0, format="%.2f"
                    )
                    price = price_cols[1].number_input(
                        "Selling price", min_value=0.0, value=float(selected_product["selling_price"]), step=1.0, format="%.2f"
                    )
                    reorder = price_cols[2].number_input(
                        "Reorder level", min_value=0.0, value=float(selected_product["reorder_level"]), step=1.0, format="%.3f"
                    )
                    st.caption(f"Current on-hand quantity: {selected_product['current_stock']}. Stock is not changed by catalog edits.")
                    submitted = st.form_submit_button("Save product changes", type="primary")
                if submitted:
                    if _show_validation_error(
                        lambda: save_product(
                            connection,
                            user["id"],
                            sku=sku,
                            name=name,
                            category_id=category_id,
                            description=description,
                            cost_price=cost,
                            selling_price=price,
                            reorder_level=reorder,
                            product_id=selected_product["id"],
                        )
                    ):
                        st.success("Product details updated.")
                        st.rerun()
        with status_tab:
            if not all_products:
                st.info("No product records are available.")
            else:
                selected_product = st.selectbox(
                    "Product",
                    options=all_products,
                    format_func=lambda item: f"{item['sku']} · {item['name']}",
                    key="status_product_selection",
                )
                action = "Reactivate" if not selected_product["is_active"] else "Deactivate"
                if st.button(f"{action} product", type="secondary", key="change_product_status"):
                    if _show_validation_error(
                        lambda: set_product_active(
                            connection,
                            user["id"],
                            selected_product["id"],
                            not selected_product["is_active"],
                        )
                    ):
                        st.success(f"Product {action.lower()}d.")
                        st.rerun()

    with category_tab:
        render_section_heading("Category management", "Organize products with reusable catalog categories.")
        add_category, edit_category, category_status = st.tabs(
            ["Add category", "Edit category", "Category status"]
        )
        with add_category:
            with st.form("create_category_form", clear_on_submit=True):
                name = st.text_input("Category name *")
                description = st.text_area("Description", max_chars=4000)
                submitted = st.form_submit_button("Create category", type="primary")
            if submitted:
                if _show_validation_error(
                    lambda: save_category(connection, user["id"], name=name, description=description)
                ):
                    st.success("Category created.")
                    st.rerun()
        with edit_category:
            if not category_rows:
                st.info("Add a category before editing.")
            else:
                selected_category = st.selectbox(
                    "Category to edit",
                    options=category_rows,
                    format_func=lambda item: item["name"],
                    key="edit_category_selection",
                )
                with st.form("edit_category_form"):
                    name = st.text_input("Category name *", value=selected_category["name"])
                    description = st.text_area(
                        "Description", value=selected_category["description"] or "", max_chars=4000
                    )
                    submitted = st.form_submit_button("Save category changes", type="primary")
                if submitted:
                    if _show_validation_error(
                        lambda: save_category(
                            connection,
                            user["id"],
                            name=name,
                            description=description,
                            category_id=selected_category["id"],
                        )
                    ):
                        st.success("Category updated.")
                        st.rerun()
        with category_status:
            if not category_rows:
                st.info("No categories are available.")
            else:
                selected_category = st.selectbox(
                    "Category",
                    options=category_rows,
                    format_func=lambda item: f"{item['name']} · {item['product_count']} products",
                    key="category_status_selection",
                )
                action = "Reactivate" if not selected_category["is_active"] else "Deactivate"
                if st.button(f"{action} category", key="change_category_status"):
                    if _show_validation_error(
                        lambda: set_category_active(
                            connection,
                            user["id"],
                            selected_category["id"],
                            not selected_category["is_active"],
                        )
                    ):
                        st.success(f"Category {action.lower()}d.")
                        st.rerun()
