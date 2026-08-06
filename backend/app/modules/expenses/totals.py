"""Expense money math, shared by the service and the ledger poster.

A tax-inclusive expense records what actually left the bank, so its tax sits
*inside* the line amounts rather than on top of them.
"""

from __future__ import annotations

from collections.abc import Sequence
from decimal import Decimal

_ZERO = Decimal("0")
_CENTS = Decimal("0.01")


def quantize(value: Decimal) -> Decimal:
    return Decimal(value).quantize(_CENTS)


def totals(
    amounts: Sequence[Decimal], tax: Decimal, *, is_tax_inclusive: bool
) -> tuple[Decimal, Decimal, Decimal]:
    gross = sum(amounts, _ZERO)
    tax = quantize(tax)
    if is_tax_inclusive:
        return gross - tax, tax, gross
    return gross, tax, gross + tax


def net_amounts(
    amounts: Sequence[Decimal], tax: Decimal, *, is_tax_inclusive: bool
) -> list[Decimal]:
    """Line amounts with any embedded tax removed, summing to the subtotal."""
    amounts = list(amounts)
    gross = sum(amounts, _ZERO)
    if not is_tax_inclusive or tax <= _ZERO or gross <= _ZERO:
        return amounts
    net = [quantize(amount - tax * amount / gross) for amount in amounts]
    net[-1] = quantize(net[-1] + (gross - tax - sum(net, _ZERO)))
    return net
