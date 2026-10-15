from __future__ import annotations

from contextlib import nullcontext
from typing import Any

import pytest

import services.navigation as navigation
from services.authorization import ADMIN, MANAGER, SALES_STAFF, STAFF


class FakeStreamlit:
    def __init__(self) -> None:
        self.sidebar = nullcontext()
        self.page_links: list[tuple[Any, str, str]] = []
        self.page_link_options: list[dict[str, Any]] = []
        self.markdown_calls: list[tuple[tuple[Any, ...], dict[str, Any]]] = []
        self.button_calls: list[tuple[tuple[Any, ...], dict[str, Any]]] = []

    def markdown(self, *args: Any, **kwargs: Any) -> None:
        self.markdown_calls.append((args, kwargs))

    def page_link(
        self,
        page: Any,
        *,
        label: str,
        icon: str,
        **kwargs: Any,
    ) -> None:
        self.page_links.append((page, label, icon))
        self.page_link_options.append(kwargs)

    def button(self, *args: Any, **kwargs: Any) -> bool:
        self.button_calls.append((args, kwargs))
        return False


@pytest.mark.parametrize(
    "role,expected_labels",
    [
        (
            ADMIN,
            [
                "Dashboard",
                "Products",
                "Customers",
                "Suppliers",
                "Inventory",
                "Sales",
                "Purchases",
                "Users",
            ],
        ),
        (
            SALES_STAFF,
            ["Dashboard", "Products", "Customers", "Sales"],
        ),
        (
            MANAGER,
            [
                "Dashboard",
                "Products",
                "Customers",
                "Suppliers",
                "Inventory",
                "Sales",
                "Purchases",
            ],
        ),
        (
            STAFF,
            ["Dashboard", "Products", "Customers", "Sales"],
        ),
    ],
)
def test_sidebar_links_to_registered_pages_for_each_role(
    monkeypatch: pytest.MonkeyPatch,
    role: str,
    expected_labels: list[str],
) -> None:
    fake_st = FakeStreamlit()
    monkeypatch.setattr(navigation, "st", fake_st)
    pages = {item["key"]: object() for item in navigation.NAV_ITEMS}

    navigation.render_sidebar(
        {"full_name": "Test User", "role": role},
        pages,
    )

    assert [label for _, label, _ in fake_st.page_links] == expected_labels
    expected_role_label = {
        ADMIN: "Admin",
        MANAGER: "Manager",
        SALES_STAFF: "Sales Staff",
        STAFF: "Staff",
    }[role]
    assert any(
        args and expected_role_label in str(args[0])
        for args, _ in fake_st.markdown_calls
    )
    for page, label, _ in fake_st.page_links:
        key = next(item["key"] for item in navigation.NAV_ITEMS if item["label"] == label)
        assert page is pages[key]
    assert all(options["width"] == "stretch" for options in fake_st.page_link_options)


def test_navigation_groups_match_the_existing_sidebar_sections() -> None:
    assert [(item["group"], item["label"]) for item in navigation.NAV_ITEMS] == [
        ("OVERVIEW", "Dashboard"),
        ("CATALOG", "Products"),
        ("RELATIONSHIPS", "Customers"),
        ("RELATIONSHIPS", "Suppliers"),
        ("OPERATIONS", "Inventory"),
        ("OPERATIONS", "Sales"),
        ("OPERATIONS", "Purchases"),
        ("ADMINISTRATION", "Users"),
    ]


@pytest.mark.parametrize(
    "role,page_key,expected",
    [
        (ADMIN, "users", True),
        (SALES_STAFF, "users", False),
        (ADMIN, "suppliers", True),
        (SALES_STAFF, "suppliers", False),
        (SALES_STAFF, "sales", True),
        (MANAGER, "sales", True),
        (STAFF, "sales", True),
        (MANAGER, "suppliers", True),
        (MANAGER, "inventory", True),
        (MANAGER, "purchases", True),
        (MANAGER, "users", False),
        (MANAGER, "unknown", False),
        (STAFF, "suppliers", False),
        (STAFF, "inventory", False),
        (STAFF, "purchases", False),
        (STAFF, "users", False),
        (SALES_STAFF, "inventory", False),
        (SALES_STAFF, "purchases", False),
        (SALES_STAFF, "users", False),
        (SALES_STAFF, "suppliers", False),
        (SALES_STAFF, "unknown", False),
    ],
)
def test_route_access_matches_page_roles(role: str, page_key: str, expected: bool) -> None:
    assert navigation.role_can_access_page(role, page_key) is expected
