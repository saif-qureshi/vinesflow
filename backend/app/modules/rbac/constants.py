"""Central definition of the permission catalog and default per-org roles.

A permission code is ``"<module>:<action>"``. The catalog is the source of truth
for both DB seeding and the `require_permission` dependency, so referencing an
undefined code anywhere is a bug we want to catch early.
"""

from __future__ import annotations

MODULE_ACTIONS: dict[str, list[str]] = {
    "orgs": ["read", "update", "delete"],
    "users": ["create", "read", "update", "delete"],
    "roles": ["create", "read", "update", "delete"],
    "sales_orders": ["create", "read", "update", "delete"],
    "delivery_challans": ["create", "read", "update", "delete"],
    "invoices": ["create", "read", "update", "delete"],
    "credit_notes": ["create", "read", "update", "delete"],
    "purchase_orders": ["create", "read", "update", "delete"],
    "goods_receipts": ["create", "read", "update", "delete"],
    "bills": ["create", "read", "update", "delete"],
    "expenses": ["create", "read", "update", "delete"],
    "parties": ["create", "read", "update", "delete"],
    "products": ["create", "read", "update", "delete"],
    "inventory": ["create", "read", "update", "delete"],
    "payments": ["create", "read", "update", "delete"],
    "accounting": ["create", "read", "update", "delete"],
    "reports": ["read"],
}

MODULE_LABELS: dict[str, str] = {
    "orgs": "Organization",
    "users": "Users",
    "roles": "Roles & Permissions",
    "sales_orders": "Sales Orders",
    "delivery_challans": "Delivery Challans",
    "invoices": "Invoices",
    "credit_notes": "Credit Notes",
    "purchase_orders": "Purchase Orders",
    "goods_receipts": "Goods Receipts",
    "bills": "Bills",
    "expenses": "Expenses",
    "parties": "Customers & Vendors",
    "products": "Products",
    "inventory": "Inventory",
    "payments": "Payments",
    "accounting": "Accounting",
    "reports": "Reports",
}


def _code(module: str, action: str) -> str:
    return f"{module}:{action}"


PERMISSION_CATALOG: list[tuple[str, str, str]] = [
    (_code(module, action), module, action)
    for module, actions in MODULE_ACTIONS.items()
    for action in actions
]

ALL_PERMISSION_CODES: set[str] = {code for code, _, _ in PERMISSION_CATALOG}


def _codes_for(modules_actions: dict[str, list[str]]) -> list[str]:
    return [_code(m, a) for m, actions in modules_actions.items() for a in actions]


DEFAULT_ROLES: dict[str, dict] = {
    "super_admin": {
        "name": "Super Admin",
        "description": "Full control over the organization, including billing and deletion.",
        "permissions": "*",
    },
    "admin": {
        "name": "Admin",
        "description": "Manage members, roles, and all business data. Cannot delete the org.",
        "permissions": sorted(ALL_PERMISSION_CODES - {"orgs:delete"}),
    },
    "member": {
        "name": "Member",
        "description": "Work with invoices, customers, products, and payments.",
        "permissions": _codes_for(
            {
                "users": ["read"],
                "sales_orders": ["create", "read", "update"],
                "delivery_challans": ["create", "read", "update"],
                "invoices": ["create", "read", "update"],
                "credit_notes": ["create", "read", "update"],
                "purchase_orders": ["create", "read", "update"],
                "goods_receipts": ["create", "read", "update"],
                "bills": ["create", "read", "update"],
                "expenses": ["create", "read", "update"],
                "parties": ["create", "read", "update"],
                "products": ["create", "read", "update"],
                "inventory": ["create", "read", "update"],
                "payments": ["create", "read"],
                "accounting": ["read"],
                "reports": ["read"],
            }
        ),
    },
    "viewer": {
        "name": "Viewer",
        "description": "Read-only access to business data.",
        "permissions": _codes_for(
            {
                "sales_orders": ["read"],
                "delivery_challans": ["read"],
                "invoices": ["read"],
                "credit_notes": ["read"],
                "purchase_orders": ["read"],
                "goods_receipts": ["read"],
                "bills": ["read"],
                "expenses": ["read"],
                "parties": ["read"],
                "products": ["read"],
                "inventory": ["read"],
                "payments": ["read"],
                "accounting": ["read"],
                "reports": ["read"],
            }
        ),
    },
}

OWNER_ROLE_SLUG = "super_admin"
