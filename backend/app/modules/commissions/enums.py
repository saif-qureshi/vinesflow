from __future__ import annotations

from enum import StrEnum

COMMISSION_PAYOUT_PREFIX = "CP-"


class CommissionPayoutStatus(StrEnum):
    DRAFT = "draft"
    SUBMITTED = "submitted"
    CANCELLED = "cancelled"
