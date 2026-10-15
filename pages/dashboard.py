"""Live inventory, sales, and purchase overview."""

from __future__ import annotations

from datetime import date, timedelta
from typing import Any

import pandas as pd
import plotly.express as px
import streamlit as st

from services.dashboard_service import get_dashboard_data
from services.authorization import (
    ADMIN,
    ADMIN_FINANCIALS,
    MANAGEMENT_DASHBOARD,
    OPERATIONS_DASHBOARD,
    SALES_FINANCIALS,
    SALES_DASHBOARD,
    role_has_permission,
)
from utils.formatters import format_currency
from utils.ui import render_kpi_card, render_page_header, render_section_heading


def _build_metric_cards(
    metrics: dict[str, Any],
    role: str,
) -> list[tuple[str, str, str]]:
    """Build a distinct dashboard KPI set using only role-authorized metrics."""
    active_products = f"{metrics['product_count']:,}"
    active_customers = f"{metrics['customer_count']:,}"
    low_stock = f"{metrics['low_stock_count']:,}"
    sales_count = f"{metrics['sales_count']:,}"
    can_view_sales_financials = role_has_permission(role, SALES_FINANCIALS)

    if role == ADMIN:
        gross_profit = metrics["gross_profit"]
        return [
            ("Active products", active_products, "Products available in catalog"),
            ("Active customers", active_customers, "Customer records"),
            (
                "Sales in period",
                format_currency(metrics["sales_total"]),
                f"{sales_count} completed invoices",
            ),
            (
                "Purchases in period",
                format_currency(metrics["purchase_total"]),
                "Non-cancelled purchases",
            ),
            (
                "Gross profit",
                format_currency(gross_profit) if gross_profit is not None else "—",
                "Sale-time costs verified"
                if gross_profit is not None
                else "Insufficient sale item cost history",
            ),
        ]
    if role_has_permission(role, MANAGEMENT_DASHBOARD):
        return [
            ("Active products", active_products, "Catalog size"),
            ("Active customers", active_customers, "Customer base"),
            ("Low-stock products", low_stock, "Require stock review"),
            (
                "Sales in period",
                format_currency(metrics["sales_total"]),
                f"{sales_count} completed invoices",
            ),
        ]
    if role_has_permission(role, SALES_DASHBOARD) and can_view_sales_financials:
        return [
            ("Active products", active_products, "Products available in catalog"),
            ("Active customers", active_customers, "Customer records"),
            (
                "Sales in period",
                format_currency(metrics["sales_total"]),
                f"{sales_count} completed invoices",
            ),
        ]
    if role_has_permission(role, OPERATIONS_DASHBOARD):
        return [
            ("Active products", active_products, "Products available for operations"),
            ("Low-stock products", low_stock, "Require stock review"),
            ("Active customers", active_customers, "Customer records"),
            ("Completed sales", sales_count, "Transactions in this period"),
        ]
    raise ValueError("Unsupported dashboard role.")


def render_dashboard(connection: Any, user: dict[str, Any], products_page: Any) -> None:
    first_name = user["full_name"].strip().split(maxsplit=1)
    if role_has_permission(user["role"], MANAGEMENT_DASHBOARD):
        title = "Management overview"
        subtitle = "Monitor catalog health, customer activity, and sales performance."
    elif role_has_permission(user["role"], OPERATIONS_DASHBOARD):
        title = "Operations overview"
        subtitle = "Track inventory readiness, low-stock products, and completed activity."
    else:
        title = f"Good to see you, {first_name[0] if first_name else 'there'}"
        subtitle = (
            "A complete view of authorized business activity."
            if user["role"] == ADMIN
            else "A clear view of your inventory and sales, all in one place."
        )
    render_page_header("Overview", title, subtitle)
    default_end = date.today()
    default_start = default_end - timedelta(days=29)
    date_columns = st.columns([1.5, 2])
    with date_columns[0]:
        selected_range = st.date_input(
            "Reporting period",
            value=(default_start, default_end),
            max_value=default_end,
            help="Sales trends, top products, and recent transactions use this inclusive date range.",
        )
    if not isinstance(selected_range, tuple) or len(selected_range) != 2:
        st.info("Choose both a start date and an end date to load dashboard analytics.")
        return
    start_date, end_date = selected_range
    try:
        with st.spinner("Loading your latest business activity…"):
            data = get_dashboard_data(connection, user["id"], start_date, end_date)
    except ValueError as exc:
        st.error(str(exc))
        return

    metrics = data["metrics"]
    can_view_sales_financials = role_has_permission(user["role"], SALES_FINANCIALS)
    cards = _build_metric_cards(metrics, user["role"])
    with st.container(key="dashboard_metrics"):
        for column, (label, value, note) in zip(st.columns(len(cards)), cards):
            with column:
                render_kpi_card(label, value, note)

    st.markdown('<div class="nx-section-spacer"></div>', unsafe_allow_html=True)
    trend_col, top_col = st.columns(2)
    with trend_col:
        render_section_heading("Sales trend", "Activity across the selected reporting period.")
        if data["sales_trend"]:
            trend = pd.DataFrame(data["sales_trend"])
            trend["day"] = pd.to_datetime(trend["day"])
            trend_value = "sales_total" if can_view_sales_financials else "sale_count"
            figure = px.area(trend, x="day", y=trend_value, color_discrete_sequence=["#641B35"])
            figure.update_traces(line={"width": 2.5}, fillcolor="rgba(100,27,53,.13)")
            figure.update_layout(
                margin={"l": 4, "r": 8, "t": 12, "b": 4},
                height=280,
                paper_bgcolor="rgba(0,0,0,0)",
                plot_bgcolor="rgba(0,0,0,0)",
                font_color="#786C75",
                xaxis_title=None,
                yaxis_title="Sales" if can_view_sales_financials else "Completed sales",
                showlegend=False,
            )
            figure.update_yaxes(gridcolor="#E8DEE3", zeroline=False)
            figure.update_xaxes(showgrid=False)
            st.plotly_chart(figure, width="stretch")
        else:
            st.markdown(
                '<div class="nx-chart-empty"><strong>No completed sales in this period</strong>'
                "<span>Sales will appear here once recorded.</span></div>",
                unsafe_allow_html=True,
            )
    with top_col:
        render_section_heading("Top-selling products", "Best performers by units sold.")
        if data["top_products"]:
            top = pd.DataFrame(data["top_products"])
            top["label"] = top["name"].str.slice(0, 34)
            figure = px.bar(
                top.sort_values("units_sold"),
                x="units_sold",
                y="label",
                orientation="h",
                color_discrete_sequence=["#C99A83"],
                hover_data=["sku"] + (["sales_total"] if can_view_sales_financials else []),
            )
            figure.update_layout(
                margin={"l": 4, "r": 8, "t": 12, "b": 4},
                height=280,
                paper_bgcolor="rgba(0,0,0,0)",
                plot_bgcolor="rgba(0,0,0,0)",
                font_color="#786C75",
                xaxis_title="Units sold",
                yaxis_title=None,
                showlegend=False,
            )
            figure.update_xaxes(gridcolor="#E8DEE3", zeroline=False)
            figure.update_yaxes(showgrid=False)
            st.plotly_chart(figure, width="stretch")
        else:
            st.markdown(
                '<div class="nx-chart-empty"><strong>No product sales in this period</strong>'
                "<span>Best sellers will appear after completed sales.</span></div>",
                unsafe_allow_html=True,
            )

    recent_col, stock_col = st.columns([1.35, 1])
    with recent_col:
        render_section_heading("Recent transactions", "Latest sales and purchases in the selected period.")
        if data["recent_transactions"]:
            transaction_table = pd.DataFrame(data["recent_transactions"])
            transaction_columns = {
                "transaction_type": "Type",
                "reference_number": "Reference",
                "counterparty": "Contact",
                "status": "Status",
                "created_at": st.column_config.DatetimeColumn("Date"),
            }
            if can_view_sales_financials:
                transaction_columns["amount"] = st.column_config.NumberColumn(
                    "Amount",
                    format="$%.2f",
                )
            st.dataframe(
                transaction_table,
                hide_index=True,
                width="stretch",
                column_config=transaction_columns,
            )
        else:
            transaction_label = (
                "sale"
                if not role_has_permission(user["role"], ADMIN_FINANCIALS)
                else "sale or purchase"
            )
            st.info(f"No {transaction_label} transactions were recorded during this period.")
    with stock_col:
        render_section_heading("Low-stock alerts", "Products at or below their reorder level.")
        if data["low_stock_products"]:
            st.caption(f"{metrics['low_stock_count']} active products are at or below reorder level.")
            st.dataframe(
                pd.DataFrame(data["low_stock_products"]),
                hide_index=True,
                width="stretch",
                column_config={
                    "sku": "SKU",
                    "name": "Product",
                    "current_stock": "On hand",
                    "reorder_level": "Reorder at",
                },
            )
            st.page_link(
                products_page,
                label="Review product catalog",
                icon=":material/inventory_2:",
            )
        else:
            st.success("No active products are currently below their reorder level.")
