"""Database-backed role checks shared by application services."""

from __future__ import annotations

from typing import Any, Iterable


class AuthorizationError(PermissionError):
    """Raised when an inactive, missing, or underprivileged account acts."""


ADMIN = "admin"
MANAGER = "manager"
SALES_STAFF = "sales_staff"
STAFF = "staff"
SUPPORTED_USER_ROLES = (ADMIN, MANAGER, SALES_STAFF, STAFF)
USER_ROLE_LABELS = {
    ADMIN: "Admin",
    MANAGER: "Manager",
    SALES_STAFF: "Sales Staff",
    STAFF: "Staff",
}

DASHBOARD_ACCESS = "dashboard"
CATALOG_READ = "catalog_read"
CUSTOMER_ACCESS = "customer_access"
SALES_ACCESS = "sales_access"
SUPPLIER_ACCESS = "supplier_access"
INVENTORY_ACCESS = "inventory_access"
PURCHASE_ACCESS = "purchase_access"
USER_ADMINISTRATION = "user_administration"
ADMIN_FINANCIALS = "admin_financials"
SALES_FINANCIALS = "sales_financials"
MANAGEMENT_DASHBOARD = "management_dashboard"
SALES_DASHBOARD = "sales_dashboard"
OPERATIONS_DASHBOARD = "operations_dashboard"

ROLE_PERMISSIONS = {
    ADMIN: frozenset(
        {
            DASHBOARD_ACCESS,
            CATALOG_READ,
            CUSTOMER_ACCESS,
            SALES_ACCESS,
            SUPPLIER_ACCESS,
            INVENTORY_ACCESS,
            PURCHASE_ACCESS,
            USER_ADMINISTRATION,
            ADMIN_FINANCIALS,
            SALES_FINANCIALS,
            MANAGEMENT_DASHBOARD,
            SALES_DASHBOARD,
            OPERATIONS_DASHBOARD,
        }
    ),
    MANAGER: frozenset(
        {
            DASHBOARD_ACCESS,
            CATALOG_READ,
            CUSTOMER_ACCESS,
            SALES_ACCESS,
            SUPPLIER_ACCESS,
            INVENTORY_ACCESS,
            PURCHASE_ACCESS,
            SALES_FINANCIALS,
            MANAGEMENT_DASHBOARD,
        }
    ),
    SALES_STAFF: frozenset(
        {
            DASHBOARD_ACCESS,
            CATALOG_READ,
            CUSTOMER_ACCESS,
            SALES_ACCESS,
            SALES_FINANCIALS,
            SALES_DASHBOARD,
        }
    ),
    STAFF: frozenset(
        {
            DASHBOARD_ACCESS,
            CATALOG_READ,
            CUSTOMER_ACCESS,
            SALES_ACCESS,
            OPERATIONS_DASHBOARD,
        }
    ),
}

PAGE_PERMISSIONS = {
    "dashboard": DASHBOARD_ACCESS,
    "products": CATALOG_READ,
    "customers": CUSTOMER_ACCESS,
    "suppliers": SUPPLIER_ACCESS,
    "inventory": INVENTORY_ACCESS,
    "sales": SALES_ACCESS,
    "purchases": PURCHASE_ACCESS,
    "users": USER_ADMINISTRATION,
}


def canonical_role(role: str) -> str:
    """Return the stored supported role unchanged for labels and dashboard selection."""
    if role not in SUPPORTED_USER_ROLES:
        raise ValueError("Unsupported user role.")
    return role


def role_has_permission(role: str, permission: str) -> bool:
    """Check the centralized permission assignment for a supported role."""
    return permission in ROLE_PERMISSIONS.get(role, frozenset())


def role_can_access_page(role: str, page_key: str) -> bool:
    """Check whether the centralized role permissions allow a registered page."""
    permission = PAGE_PERMISSIONS.get(page_key)
    return permission is not None and role_has_permission(role, permission)


def _active_user(connection: Any, user_id: int) -> dict[str, Any]:
    cursor = connection.cursor(dictionary=True)
    try:
        cursor.execute(
            "SELECT id, username, full_name, role, is_active FROM users WHERE id = %s",
            (user_id,),
        )
        actor = cursor.fetchone()
    finally:
        cursor.close()
    if actor is None or not actor["is_active"]:
        raise AuthorizationError("This account is inactive or no longer exists.")
    if actor["role"] not in SUPPORTED_USER_ROLES:
        raise AuthorizationError("This account has an unsupported role.")
    return actor


def require_permission(connection: Any, user_id: int, permission: str) -> dict[str, Any]:
    """Reload the active user and enforce a named centralized permission."""
    actor = _active_user(connection, user_id)
    if not role_has_permission(actor["role"], permission):
        raise AuthorizationError("You do not have permission to perform this action.")
    return actor


def require_role(connection: Any, user_id: int, allowed_roles: Iterable[str]) -> dict[str, Any]:
    """Retain an exact-role guard for callers that explicitly need it."""
    actor = _active_user(connection, user_id)
    if actor["role"] not in set(allowed_roles):
        raise AuthorizationError("You do not have permission to perform this action.")
    return actor


def require_admin(connection: Any, user_id: int) -> dict[str, Any]:
    return require_permission(connection, user_id, USER_ADMINISTRATION)


def require_catalog_read(connection: Any, user_id: int) -> dict[str, Any]:
    return require_permission(connection, user_id, CATALOG_READ)


def require_customer_access(connection: Any, user_id: int) -> dict[str, Any]:
    return require_permission(connection, user_id, CUSTOMER_ACCESS)


def require_supplier_access(connection: Any, user_id: int) -> dict[str, Any]:
    return require_permission(connection, user_id, SUPPLIER_ACCESS)


def require_inventory_access(connection: Any, user_id: int) -> dict[str, Any]:
    return require_permission(connection, user_id, INVENTORY_ACCESS)


def require_purchase_access(connection: Any, user_id: int) -> dict[str, Any]:
    return require_permission(connection, user_id, PURCHASE_ACCESS)
