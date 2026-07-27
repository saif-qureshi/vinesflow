from __future__ import annotations

from enum import StrEnum

EXPENSE_PREFIX = "EXP-"


class ExpenseStatus(StrEnum):
    DRAFT = "draft"
    SUBMITTED = "submitted"
    CANCELLED = "cancelled"
