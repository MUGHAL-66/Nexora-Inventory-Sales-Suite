from __future__ import annotations

from datetime import date
from decimal import Decimal

import bcrypt
import pytest
from mysql.connector.errors import IntegrityError, ProgrammingError

from pages.dashboard import _build_metric_cards
from services.auth_service import (
    authenticate,
    create_user,
    deactivate_user,
    get_active_user,
    list_users,
)
from services.authorization import (
    ADMIN,
    ADMIN_FINANCIALS,
    DASHBOARD_ACCESS,
    INVENTORY_ACCESS,
    MANAGER,
    PURCHASE_ACCESS,
    SALES_STAFF,
    SALES_FINANCIALS,
    STAFF,
    SUPPLIER_ACCESS,
    SUPPORTED_USER_ROLES,
    USER_ROLE_LABELS,
    AuthorizationError,
    require_admin,
    role_has_permission,
)
from services.catalog_service import (
    adjust_stock,
    list_products,
    list_stock_transactions,
    save_product,
)
from services.contacts_service import (
    list_supplier_history,
    list_suppliers,
    save_customer,
    save_supplier,
    set_supplier_active,
)
from services.dashboard_service import get_dashboard_data
from services.purchases_service import (
    create_purchase,
    get_purchase_detail,
    list_purchases,
)
from services.sales_service import create_sale


class FakeCursor:
    def __init__(
        self,
        *,
        one: list[object] | None = None,
        many: list[list[object]] | None = None,
        fail_on: str | None = None,
    ) -> None:
        self.one = list(one or [])
        self.many = list(many or [])
        self.fail_on = fail_on
        self.statements: list[tuple[str, tuple]] = []
        self.lastrowid = 12
        self.rowcount = 1
        self.closed = False

    def execute(self, sql: str, parameters: tuple = ()) -> None:
        self.statements.append((sql, parameters))
        if self.fail_on and self.fail_on in sql:
            raise IntegrityError(errno=1062, msg="Duplicate entry")

    def fetchone(self):
        return self.one.pop(0) if self.one else None

    def fetchall(self):
        return self.many.pop(0) if self.many else []

    def close(self) -> None:
        self.closed = True


class FakeConnection:
    def __init__(self, cursors: list[FakeCursor]) -> None:
        self.cursors = list(cursors)
        self.executed: list[FakeCursor] = []
        self.commits = 0
        self.rollbacks = 0
        self.transactions = 0
        self.in_transaction = False

    def cursor(self, *, dictionary: bool = False) -> FakeCursor:
        assert isinstance(dictionary, bool)
        cursor = self.cursors.pop(0)
        self.executed.append(cursor)
        return cursor

    def commit(self) -> None:
        self.commits += 1
        self.in_transaction = False

    def rollback(self) -> None:
        self.rollbacks += 1
        self.in_transaction = False

    def start_transaction(self) -> None:
        if self.in_transaction:
            raise ProgrammingError("Transaction already in progress")
        self.transactions += 1
        self.in_transaction = True


def admin_cursor() -> FakeCursor:
    return FakeCursor(
        one=[{"id": 1, "username": "admin", "full_name": "Admin", "role": "admin", "is_active": 1}]
    )


def sales_staff_cursor(*, active: int = 1) -> FakeCursor:
    return FakeCursor(
        one=[{
            "id": 2,
            "username": "clerk",
            "full_name": "Sales Clerk",
            "role": "sales_staff",
            "is_active": active,
        }]
    )


def role_cursor(role: str, *, active: int = 1) -> FakeCursor:
    return FakeCursor(
        one=[
            {
                "id": 2,
                "username": f"{role}_user",
                "full_name": f"{role.title()} User",
                "role": role,
                "is_active": active,
            }
        ]
    )


@pytest.mark.parametrize(
    "stored_role",
    [
        ADMIN,
        MANAGER,
        SALES_STAFF,
        STAFF,
    ],
)
def test_authentication_preserves_each_stored_role(stored_role: str) -> None:
    password_hash = bcrypt.hashpw(b"correct horse battery", bcrypt.gensalt()).decode()
    connection = FakeConnection(
        [FakeCursor(one=[{
            "id": 5,
            "username": "nora",
            "full_name": "Nora Sales",
            "password_hash": password_hash,
            "role": stored_role,
            "is_active": 1,
        }])]
    )
    user = authenticate(connection, " nora ", "correct horse battery")
    assert user == {
        "id": 5,
        "username": "nora",
        "full_name": "Nora Sales",
        "role": stored_role,
    }
    assert "password_hash" not in user


@pytest.mark.parametrize("stored_role", [MANAGER, STAFF])
def test_active_session_refresh_preserves_current_database_role(stored_role: str) -> None:
    connection = FakeConnection(
        [
            FakeCursor(
                one=[
                    {
                        "id": 5,
                        "username": "nora",
                        "full_name": "Nora",
                        "role": stored_role,
                        "is_active": 1,
                    }
                ]
            )
        ]
    )

    assert get_active_user(connection, 5)["role"] == stored_role


@pytest.mark.parametrize("role", [ADMIN, MANAGER, SALES_STAFF, STAFF])
def test_dashboard_permission_is_defined_for_all_four_roles(role: str) -> None:
    assert role_has_permission(role, DASHBOARD_ACCESS)


@pytest.mark.parametrize("role", [MANAGER, SALES_STAFF])
def test_manager_and_sales_staff_dashboard_permissions_exclude_admin_financials(
    role: str,
) -> None:
    assert role_has_permission(role, SALES_FINANCIALS)
    assert not role_has_permission(role, ADMIN_FINANCIALS)


def test_staff_dashboard_is_operational_and_excludes_financial_permissions() -> None:
    assert role_has_permission(STAFF, "operations_dashboard")
    assert not role_has_permission(STAFF, SALES_FINANCIALS)
    assert not role_has_permission(STAFF, ADMIN_FINANCIALS)


@pytest.mark.parametrize("stored_role", [ADMIN, MANAGER, SALES_STAFF, STAFF])
def test_user_creation_accepts_and_persists_each_supported_role(stored_role: str) -> None:
    insert_cursor = FakeCursor()
    connection = FakeConnection([admin_cursor(), insert_cursor])

    user_id = create_user(
        connection,
        1,
        username=f"{stored_role}_user",
        email=f"{stored_role}@example.com",
        full_name=f"{stored_role.title()} User",
        role=stored_role,
        password="a sufficiently long password",
    )

    assert user_id == 12
    assert connection.commits == 1
    assert insert_cursor.statements[0][1][-1] == stored_role
    assert insert_cursor.closed


def test_user_creation_rejects_unknown_roles_before_writing() -> None:
    connection = FakeConnection([admin_cursor()])

    with pytest.raises(ValueError, match="Admin, Manager, Sales Staff, or Staff"):
        create_user(
            connection,
            1,
            username="unknown_role",
            email="unknown@example.com",
            full_name="Unknown Role",
            role="owner",
            password="a sufficiently long password",
        )

    assert len(connection.cursors) == 0


def test_user_management_role_choices_include_exact_database_roles() -> None:
    assert SUPPORTED_USER_ROLES == ("admin", "manager", "sales_staff", "staff")
    assert tuple(USER_ROLE_LABELS[role] for role in SUPPORTED_USER_ROLES) == (
        "Admin",
        "Manager",
        "Sales Staff",
        "Staff",
    )


@pytest.mark.parametrize("stored_role", [MANAGER, STAFF])
def test_user_listing_preserves_the_stored_role_label(stored_role: str) -> None:
    account = {
        "id": 3,
        "username": "existing_user",
        "email": "existing@example.com",
        "full_name": "Existing User",
        "role": stored_role,
        "is_active": 1,
    }
    connection = FakeConnection(
        [
            admin_cursor(),
            FakeCursor(many=[[account]]),
        ]
    )

    users = list_users(connection, 1)

    assert users[0]["role"] == stored_role


@pytest.mark.parametrize("stored_role", [MANAGER, STAFF])
def test_non_admin_roles_do_not_receive_administrator_permissions(stored_role: str) -> None:
    account = FakeCursor(
        one=[{"id": 2, "username": "worker", "full_name": "Worker", "role": stored_role, "is_active": 1}]
    )

    with pytest.raises(AuthorizationError, match="permission"):
        require_admin(FakeConnection([account]), 2)


@pytest.mark.parametrize("active,password", [(0, "correct horse battery"), (1, "wrong password")])
def test_authentication_rejects_inactive_and_wrong_password(active: int, password: str) -> None:
    password_hash = bcrypt.hashpw(b"correct horse battery", bcrypt.gensalt()).decode()
    connection = FakeConnection(
        [FakeCursor(one=[{
            "id": 5,
            "username": "nora",
            "full_name": "Nora Sales",
            "password_hash": password_hash,
            "role": "sales_staff",
            "is_active": active,
        }])]
    )
    assert authenticate(connection, "nora", password) is None


def test_inactive_actor_cannot_call_admin_service() -> None:
    with pytest.raises(AuthorizationError, match="inactive"):
        require_admin(FakeConnection([sales_staff_cursor(active=0)]), 2)


def test_sales_staff_cannot_call_admin_service() -> None:
    with pytest.raises(AuthorizationError, match="permission"):
        require_admin(FakeConnection([sales_staff_cursor()]), 2)


def test_sale_creation_rolls_back_sale_items_and_stock_when_item_insert_fails() -> None:
    cursor = FakeCursor(
        one=[
            {
                "id": 4,
                "sku": "SKU-4",
                "name": "Widget",
                "cost_price": Decimal("12.00"),
                "selling_price": Decimal("20.00"),
                "current_stock": Decimal("5.000"),
            }
        ],
        fail_on="INSERT INTO inventory_transactions",
    )
    connection = FakeConnection([sales_staff_cursor(), cursor])

    with pytest.raises(IntegrityError):
        create_sale(
            connection,
            2,
            customer_id=None,
            items=[{"product_id": 4, "quantity": 2}],
        )

    assert connection.transactions == 1
    assert connection.commits == 0
    assert connection.rollbacks == 1
    assert connection.in_transaction is False
    assert any("INSERT INTO sales" in query for query, _ in cursor.statements)
    assert any("INSERT INTO sale_items" in query for query, _ in cursor.statements)
    assert any("UPDATE products SET current_stock" in query for query, _ in cursor.statements)
    assert any("INSERT INTO inventory_transactions" in query for query, _ in cursor.statements)


def test_sale_creation_commits_sale_items_and_stock_as_one_transaction() -> None:
    cursor = FakeCursor(
        one=[
            {
                "id": 4,
                "sku": "SKU-4",
                "name": "Widget",
                "cost_price": Decimal("12.00"),
                "selling_price": Decimal("20.00"),
                "current_stock": Decimal("5.000"),
            }
        ]
    )
    connection = FakeConnection([sales_staff_cursor(), cursor])

    sale_id = create_sale(
        connection,
        2,
        customer_id=None,
        items=[{"product_id": 4, "quantity": 2}],
    )

    assert sale_id == 12
    assert connection.transactions == 1
    assert connection.commits == 1
    assert connection.rollbacks == 0
    assert connection.in_transaction is False
    assert any("INSERT INTO sales" in query for query, _ in cursor.statements)
    assert any("INSERT INTO sale_items" in query for query, _ in cursor.statements)
    assert any("UPDATE products SET current_stock" in query for query, _ in cursor.statements)
    assert any("INSERT INTO inventory_transactions" in query for query, _ in cursor.statements)


def test_sale_creation_does_not_rollback_a_transaction_it_did_not_start() -> None:
    connection = FakeConnection(
        [
            sales_staff_cursor(),
            FakeCursor(one=[]),
        ]
    )
    connection.in_transaction = True

    with pytest.raises(ProgrammingError, match="Transaction already in progress"):
        create_sale(
            connection,
            2,
            customer_id=None,
            items=[{"product_id": 4, "quantity": 2}],
        )

    assert connection.transactions == 0
    assert connection.commits == 0
    assert connection.rollbacks == 0
    assert connection.in_transaction is True


def test_product_duplicate_sku_is_translated_to_validation_error_and_rolled_back() -> None:
    connection = FakeConnection([admin_cursor(), FakeCursor(fail_on="INSERT INTO products")])
    with pytest.raises(ValueError, match="SKU is already in use"):
        save_product(
            connection,
            1,
            sku="SKU-001",
            name="Desk light",
            category_id=None,
            description="",
            cost_price="12.00",
            selling_price="20.00",
            reorder_level="2",
        )
    assert connection.rollbacks == 1


def test_product_price_and_stock_validation_prevents_invalid_database_writes() -> None:
    connection = FakeConnection([admin_cursor()])
    with pytest.raises(ValueError, match="non-negative"):
        save_product(
            connection,
            1,
            sku="SKU-001",
            name="Desk light",
            category_id=None,
            description="",
            cost_price="-1",
            selling_price="20",
            reorder_level="2",
        )
    assert len(connection.cursors) == 0


def test_product_update_does_not_write_current_stock() -> None:
    connection = FakeConnection(
        [
            admin_cursor(),
            FakeCursor(one=[(12,)]),
        ]
    )
    save_product(
        connection,
        1,
        sku="SKU-001",
        name="Desk light",
        category_id=None,
        description="",
        cost_price="12.00",
        selling_price="20.00",
        reorder_level="2",
        product_id=12,
    )
    update_sql = connection.executed[-1].statements[-1][0].lower()
    assert "update products" in update_sql
    assert "current_stock" not in update_sql


def test_product_edit_can_preserve_its_existing_inactive_category() -> None:
    connection = FakeConnection(
        [
            admin_cursor(),
            FakeCursor(one=[(9,), (12,)]),
        ]
    )
    save_product(
        connection,
        1,
        sku="SKU-001",
        name="Desk light",
        category_id=9,
        description="",
        cost_price="12.00",
        selling_price="20.00",
        reorder_level="2",
        product_id=12,
    )
    assert "UPDATE products" in connection.executed[-1].statements[-1][0]


def test_sales_staff_catalog_query_redacts_cost_price() -> None:
    products_cursor = FakeCursor(many=[[]])
    connection = FakeConnection([sales_staff_cursor(), products_cursor])
    list_products(connection, 2)
    sql = products_cursor.statements[0][0]
    assert "NULL AS cost_price" in sql
    assert "p.cost_price" not in sql


def test_stock_adjustment_updates_balance_and_appends_audited_transaction() -> None:
    stock_cursor = FakeCursor(one=[{"current_stock": Decimal("3.000")}])
    connection = FakeConnection([admin_cursor(), stock_cursor])
    new_stock = adjust_stock(
        connection,
        1,
        product_id=12,
        quantity_change="2.500",
        notes="Count correction",
    )
    assert new_stock == Decimal("5.500")
    statements = stock_cursor.statements
    assert "UPDATE products SET current_stock" in statements[1][0]
    assert "INSERT INTO inventory_transactions" in statements[2][0]
    assert statements[2][1][3:] == (Decimal("2.500"), Decimal("5.500"), "Count correction")
    assert connection.transactions == 1
    assert connection.commits == 1


def test_customer_validation_rejects_invalid_phone_before_write() -> None:
    connection = FakeConnection([sales_staff_cursor()])
    with pytest.raises(ValueError, match="Phone"):
        save_customer(
            connection,
            2,
            name="Nora Customer",
            email="nora@example.com",
            phone="not a phone",
        )
    assert len(connection.cursors) == 0


def test_customer_duplicate_email_is_reported_without_insert() -> None:
    connection = FakeConnection(
        [
            sales_staff_cursor(),
            FakeCursor(one=[(9,)]),
        ]
    )
    with pytest.raises(ValueError, match="already uses"):
        save_customer(
            connection,
            2,
            name="Another customer",
            email="existing@example.com",
        )
    assert connection.commits == 0


def test_supplier_validation_rejects_invalid_email_before_write() -> None:
    connection = FakeConnection([admin_cursor()])
    with pytest.raises(ValueError, match="email"):
        save_supplier(
            connection,
            1,
            name="Northwind",
            email="invalid",
        )
    assert len(connection.cursors) == 0


def test_supplier_duplicate_email_is_reported_without_insert() -> None:
    connection = FakeConnection(
        [
            admin_cursor(),
            FakeCursor(one=[(9,)]),
        ]
    )
    with pytest.raises(ValueError, match="already uses"):
        save_supplier(
            connection,
            1,
            name="Another supplier",
            email="existing@example.com",
        )
    assert connection.commits == 0


def test_admin_cannot_deactivate_self() -> None:
    connection = FakeConnection([admin_cursor()])
    with pytest.raises(ValueError, match="own account"):
        deactivate_user(connection, 1, 1)
    assert connection.transactions == 0


def test_last_active_admin_cannot_be_deactivated() -> None:
    connection = FakeConnection(
        [
            admin_cursor(),
            FakeCursor(one=[{"id": 1, "role": "admin", "is_active": 1}]),
            FakeCursor(many=[[]]),
        ]
    )
    with pytest.raises(ValueError, match="last active administrator"):
        deactivate_user(connection, 1, 7)
    assert connection.rollbacks == 1


def test_dashboard_uses_inclusive_dates_and_hides_admin_financial_metrics_from_staff() -> None:
    period = (date(2026, 10, 1), date(2026, 10, 3))
    metrics = {
        "product_count": 4,
        "customer_count": 2,
        "low_stock_count": 1,
        "sales_total": Decimal("120.00"),
        "sales_count": 2,
    }
    dashboard_cursor = FakeCursor(
        one=[metrics],
        many=[[], [], [{"transaction_type": "Sale"}], []],
    )
    connection = FakeConnection([sales_staff_cursor(), dashboard_cursor])
    result = get_dashboard_data(connection, 2, *period)
    assert result["metrics"]["sales_total"] == Decimal("120.00")
    assert "purchase_total" not in result["metrics"]
    assert "gross_profit" not in result["metrics"]
    assert all("purchases" not in sql.lower() for sql, _ in dashboard_cursor.statements)
    summary_parameters = dashboard_cursor.statements[0][1]
    assert summary_parameters == (period[0], date(2026, 10, 4), period[0], date(2026, 10, 4))


def test_admin_dashboard_shows_gross_profit_only_with_cost_for_every_sale() -> None:
    period = (date(2026, 10, 1), date(2026, 10, 1))
    metrics = {
        "product_count": 1,
        "customer_count": 1,
        "low_stock_count": 0,
        "sales_total": Decimal("50.00"),
        "sales_count": 1,
    }
    cursor = FakeCursor(
        one=[
            metrics,
            {"purchase_total": Decimal("18.00")},
            {
                "sales_count": 2,
                "costed_sales": 1,
                "gross_profit": Decimal("9.00"),
            },
        ],
        many=[[], [], [], []],
    )
    connection = FakeConnection([admin_cursor(), cursor])
    data = get_dashboard_data(connection, 1, *period)
    assert data["metrics"]["purchase_total"] == Decimal("18.00")
    assert data["metrics"]["gross_profit"] is None
    assert any("FROM purchases" in sql for sql, _ in cursor.statements)


@pytest.mark.parametrize("role", ["sales_staff", "manager", "staff"])
def test_non_admin_dashboard_omits_purchase_and_profit_metrics(role: str) -> None:
    period = (date(2026, 10, 1), date(2026, 10, 1))
    summary = {
        "product_count": 0,
        "customer_count": 0,
        "low_stock_count": 0,
        "sales_total": Decimal("0.00"),
        "sales_count": 0,
    }
    actor = FakeCursor(
        one=[{"id": 2, "username": "clerk", "full_name": "Clerk", "role": role, "is_active": 1}]
    )
    dashboard_cursor = FakeCursor(one=[summary], many=[[], [], [], []])

    result = get_dashboard_data(FakeConnection([actor, dashboard_cursor]), 2, *period)

    assert "purchase_total" not in result["metrics"]
    assert "gross_profit" not in result["metrics"]
    queries = [sql.lower() for sql, _ in dashboard_cursor.statements]
    assert not any("purchases" in sql or "unit_cost" in sql for sql in queries)
    if role == STAFF:
        assert "sales_total" not in result["metrics"]
        assert all("sum(total)" not in query and "line_total" not in query for query in queries)
        assert all("amount" not in record for record in result["recent_transactions"])
    else:
        assert result["metrics"]["sales_total"] == Decimal("0.00")


def test_admin_empty_purchase_aggregate_is_numeric_and_gross_profit_is_unavailable() -> None:
    period = (date(2026, 10, 1), date(2026, 10, 1))
    summary = {
        "product_count": 0,
        "customer_count": 0,
        "low_stock_count": 0,
        "sales_total": Decimal("0.00"),
        "sales_count": 0,
    }
    cursor = FakeCursor(
        one=[
            summary,
            {"purchase_total": Decimal("0.00")},
            {"sales_count": 0, "costed_sales": 0, "gross_profit": None},
        ],
        many=[[], [], [], []],
    )

    data = get_dashboard_data(FakeConnection([admin_cursor(), cursor]), 1, *period)

    assert data["metrics"]["sales_total"] == Decimal("0.00")
    assert data["metrics"]["purchase_total"] == Decimal("0.00")
    assert data["metrics"]["gross_profit"] is None
    assert "COALESCE(SUM(total), 0)" in cursor.statements[1][0]


@pytest.mark.parametrize(
    "role,expected_labels",
    [
        ("sales_staff", {"Active products", "Active customers", "Sales in period"}),
        (
            "manager",
            {
                "Active products",
                "Active customers",
                "Low-stock products",
                "Sales in period",
            },
        ),
        (
            "staff",
            {
                "Active products",
                "Active customers",
                "Low-stock products",
                "Completed sales",
            },
        ),
    ],
)
def test_dashboard_cards_match_role_profile(
    role: str,
    expected_labels: set[str],
) -> None:
    cards = _build_metric_cards(
        {
            "product_count": 0,
            "customer_count": 0,
            "low_stock_count": 0,
            "sales_total": Decimal("0.00"),
            "sales_count": 0,
        },
        role,
    )

    labels = {label for label, _, _ in cards}
    assert labels == expected_labels
    assert all("purchase" not in label.lower() and "profit" not in label.lower() for label in labels)


def test_dashboard_cards_render_empty_admin_aggregates_without_crashing() -> None:
    cards = _build_metric_cards(
        {
            "product_count": 0,
            "customer_count": 0,
            "low_stock_count": 0,
            "sales_total": Decimal("0.00"),
            "sales_count": 0,
            "purchase_total": Decimal("0.00"),
            "gross_profit": None,
        },
        "admin",
    )

    values = {label: value for label, value, _ in cards}
    assert values["Sales in period"] == "USD 0.00"
    assert values["Purchases in period"] == "USD 0.00"
    assert values["Gross profit"] == "—"


def test_dashboard_rejects_reversed_date_range_before_database_query() -> None:
    connection = FakeConnection([admin_cursor()])
    with pytest.raises(ValueError, match="on or after"):
        get_dashboard_data(connection, 1, date(2026, 10, 3), date(2026, 10, 1))


@pytest.mark.parametrize(
    "role,expected_permissions",
    [
        (
            ADMIN,
            {SUPPLIER_ACCESS, INVENTORY_ACCESS, PURCHASE_ACCESS, ADMIN_FINANCIALS},
        ),
        (
            MANAGER,
            {SUPPLIER_ACCESS, INVENTORY_ACCESS, PURCHASE_ACCESS},
        ),
        (SALES_STAFF, set()),
        (STAFF, set()),
    ],
)
def test_operational_permission_matrix(role: str, expected_permissions: set[str]) -> None:
    actual = {
        permission
        for permission in (
            SUPPLIER_ACCESS,
            INVENTORY_ACCESS,
            PURCHASE_ACCESS,
            ADMIN_FINANCIALS,
        )
        if role_has_permission(role, permission)
    }
    assert actual == expected_permissions


def test_manager_supplier_directory_omits_purchase_financials() -> None:
    supplier = {
        "id": 7,
        "supplier_code": "SUP-7",
        "name": "Northwind",
        "email": None,
        "phone": None,
        "address": None,
        "is_active": 1,
        "created_at": None,
        "updated_at": None,
    }
    cursor = FakeCursor(many=[[supplier]])
    result = list_suppliers(FakeConnection([role_cursor(MANAGER), cursor]), 2)

    assert result == [supplier]
    query = cursor.statements[0][0].lower()
    assert "purchase_total" not in query
    assert "from purchases" not in query
    assert "purchase_total" not in result[0]


def test_admin_supplier_directory_retains_purchase_summary() -> None:
    supplier = {
        "id": 7,
        "supplier_code": "SUP-7",
        "name": "Northwind",
        "email": None,
        "phone": None,
        "address": None,
        "is_active": 1,
        "created_at": None,
        "updated_at": None,
        "purchase_count": 3,
        "purchase_total": Decimal("123.45"),
    }
    cursor = FakeCursor(many=[[supplier]])
    result = list_suppliers(FakeConnection([admin_cursor(), cursor]), 1)

    assert result[0]["purchase_total"] == Decimal("123.45")
    assert "purchase_total" in cursor.statements[0][0].lower()


def test_manager_can_create_and_edit_supplier_records() -> None:
    create_connection = FakeConnection(
        [role_cursor(MANAGER), FakeCursor(one=[]), FakeCursor()]
    )
    supplier_id = save_supplier(
        create_connection,
        2,
        name="Northwind",
        email="supplier@example.com",
    )
    assert supplier_id == 12
    assert create_connection.commits == 1

    edit_connection = FakeConnection(
        [
            role_cursor(MANAGER),
            FakeCursor(one=[(12,)]),
            FakeCursor(),
        ]
    )
    updated_id = save_supplier(
        edit_connection,
        2,
        name="Northwind Updated",
        supplier_id=12,
    )
    assert updated_id == 12
    assert edit_connection.commits == 1

    status_connection = FakeConnection([role_cursor(MANAGER), FakeCursor()])
    set_supplier_active(status_connection, 2, 12, False)
    assert status_connection.commits == 1


@pytest.mark.parametrize("role", [SALES_STAFF, STAFF])
def test_non_manager_roles_cannot_manage_supplier_records(role: str) -> None:
    with pytest.raises(AuthorizationError, match="permission"):
        save_supplier(
            FakeConnection([role_cursor(role)]),
            2,
            name="Restricted supplier",
        )
    with pytest.raises(AuthorizationError, match="permission"):
        set_supplier_active(
            FakeConnection([role_cursor(role)]),
            2,
            7,
            False,
        )


def test_manager_purchase_history_omits_financial_fields() -> None:
    row = {
        "id": 9,
        "purchase_number": "PO-9",
        "supplier_id": 7,
        "supplier_name": "Northwind",
        "created_by_user_id": 2,
        "created_by": "Manager User",
        "receiving_status": "received",
        "payment_status": "unpaid",
        "created_at": None,
    }
    cursor = FakeCursor(many=[[row]])
    result = list_purchases(FakeConnection([role_cursor(MANAGER), cursor]), 2)

    assert result == [row]
    query = cursor.statements[0][0].lower()
    assert "subtotal" not in query
    assert "p.total" not in query


def test_admin_purchase_history_retains_financial_fields() -> None:
    purchase = {
        "id": 9,
        "purchase_number": "PO-9",
        "supplier_id": 7,
        "supplier_name": "Northwind",
        "created_by_user_id": 1,
        "created_by": "Admin",
        "receiving_status": "received",
        "payment_status": "paid",
        "subtotal": Decimal("100.00"),
        "total": Decimal("100.00"),
        "created_at": None,
    }
    cursor = FakeCursor(many=[[purchase]])
    result = list_purchases(FakeConnection([admin_cursor(), cursor]), 1)

    assert result[0]["total"] == Decimal("100.00")
    assert "p.total" in cursor.statements[0][0].lower()


def test_manager_purchase_detail_omits_totals_and_line_costs() -> None:
    purchase = {
        "id": 9,
        "purchase_number": "PO-9",
        "supplier_id": 7,
        "supplier_name": "Northwind",
        "created_by_user_id": 2,
        "created_by": "Manager User",
        "receiving_status": "received",
        "payment_status": "unpaid",
        "notes": None,
        "created_at": None,
    }
    item = {
        "id": 1,
        "sku": "SKU-1",
        "product_name": "Widget",
        "quantity_ordered": Decimal("2"),
        "quantity_received": Decimal("2"),
    }
    cursor = FakeCursor(one=[purchase], many=[[item]])
    result = get_purchase_detail(
        FakeConnection([role_cursor(MANAGER), cursor]),
        2,
        9,
    )

    assert result == {**purchase, "items": [item]}
    queries = "\n".join(query.lower() for query, _ in cursor.statements)
    assert "p.total" not in queries
    assert "p.subtotal" not in queries
    assert "unit_cost" not in queries
    assert "line_total" not in queries


def test_manager_purchase_create_uses_stored_product_cost_without_returning_it() -> None:
    cursor = FakeCursor(
        one=[
            {"id": 7},
            {
                "id": 4,
                "sku": "SKU-4",
                "name": "Widget",
                "cost_price": Decimal("12.34"),
                "selling_price": Decimal("20.00"),
                "current_stock": Decimal("3.000"),
                "is_active": True,
            },
        ]
    )
    connection = FakeConnection([role_cursor(MANAGER), cursor])

    purchase_id = create_purchase(
        connection,
        2,
        supplier_id=7,
        items=[
            {
                "product_id": 4,
                "quantity_ordered": 2,
                "quantity_received": 1.5,
            }
        ],
        receiving_status="partially_received",
    )

    assert purchase_id == 12
    assert connection.commits == 1
    purchase_item_write = next(
        parameters
        for query, parameters in cursor.statements
        if "INSERT INTO purchase_items" in query
    )
    assert purchase_item_write[4] == Decimal("12.34")
    assert purchase_item_write[5] == Decimal("24.68")
    inventory_update = next(
        parameters
        for query, parameters in cursor.statements
        if query.startswith("UPDATE products SET current_stock")
    )
    assert inventory_update == (
        Decimal("4.500"),
        Decimal("12.34"),
        4,
    )


def test_manager_cannot_override_purchase_cost_in_service_call() -> None:
    cursor = FakeCursor(one=[{"id": 7}])
    connection = FakeConnection([role_cursor(MANAGER), cursor])

    with pytest.raises(AuthorizationError, match="cannot set purchase costs"):
        create_purchase(
            connection,
            2,
            supplier_id=7,
            items=[
                {
                    "product_id": 4,
                    "quantity_ordered": 1,
                    "quantity_received": 1,
                    "unit_cost": Decimal("0.01"),
                }
            ],
        )

    assert connection.commits == 0
    assert connection.rollbacks == 1
    assert not any("FROM products" in query for query, _ in cursor.statements)


@pytest.mark.parametrize("role", [SALES_STAFF, STAFF])
def test_sales_and_staff_cannot_access_purchase_services(role: str) -> None:
    with pytest.raises(AuthorizationError, match="permission"):
        list_purchases(FakeConnection([role_cursor(role)]), 2)
    with pytest.raises(AuthorizationError, match="permission"):
        create_purchase(
            FakeConnection([role_cursor(role)]),
            2,
            supplier_id=1,
            items=[{"product_id": 1, "quantity_ordered": 1}],
        )


def test_manager_can_view_inventory_history_but_cannot_manually_adjust_stock() -> None:
    history_cursor = FakeCursor(many=[[]])
    result = list_stock_transactions(
        FakeConnection([role_cursor(MANAGER), history_cursor]),
        2,
    )
    assert result == []

    with pytest.raises(AuthorizationError, match="permission"):
        adjust_stock(
            FakeConnection([role_cursor(MANAGER)]),
            2,
            product_id=1,
            quantity_change=1,
            notes="Attempted restricted adjustment",
        )


def test_sales_staff_cannot_directly_open_manager_operational_services() -> None:
    for role in (SALES_STAFF, STAFF):
        for service_call in (
            lambda role=role: list_suppliers(FakeConnection([role_cursor(role)]), 2),
            lambda role=role: list_stock_transactions(
                FakeConnection([role_cursor(role)]), 2
            ),
            lambda role=role: list_purchases(FakeConnection([role_cursor(role)]), 2),
        ):
            with pytest.raises(AuthorizationError, match="permission"):
                service_call()


def test_manager_cannot_open_admin_only_user_management_or_supplier_cost_history() -> None:
    with pytest.raises(AuthorizationError, match="permission"):
        list_users(FakeConnection([role_cursor(MANAGER)]), 2)
    with pytest.raises(AuthorizationError, match="permission"):
        list_supplier_history(FakeConnection([role_cursor(MANAGER)]), 2, 7)
