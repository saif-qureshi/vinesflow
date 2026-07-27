from __future__ import annotations

from datetime import date
from decimal import Decimal

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.core.exceptions import NotFoundError
from app.modules.accounting.models import Account, FiscalYear, LedgerEntry

_ZERO = Decimal("0")


class ReportsService:
    """Read-only financial statements built from the posted ledger.

    Every posted voucher balances, so Trial Balance always ties and the Balance
    Sheet balances once current-period earnings (unclosed income − expense) are
    folded into equity — year-end closing moves those into retained earnings.
    """

    def __init__(self, db: Session) -> None:
        self.db = db

    # --- shared -----------------------------------------------------------

    def _account_rows(self, org_id: int, *, start: date | None = None, end: date | None = None):
        stmt = (
            select(
                Account.id,
                Account.code,
                Account.name,
                Account.account_type,
                func.coalesce(func.sum(LedgerEntry.debit), 0),
                func.coalesce(func.sum(LedgerEntry.credit), 0),
            )
            .join(LedgerEntry, LedgerEntry.account_id == Account.id)
            .where(Account.org_id == org_id, LedgerEntry.org_id == org_id)
            .group_by(Account.id)
            .order_by(Account.code)
        )
        if start is not None:
            stmt = stmt.where(LedgerEntry.posting_date >= start)
        if end is not None:
            stmt = stmt.where(LedgerEntry.posting_date <= end)
        return self.db.execute(stmt).all()

    def current_fiscal_year(self, org_id: int, target: date) -> FiscalYear | None:
        return self.db.scalar(
            select(FiscalYear).where(
                FiscalYear.org_id == org_id,
                FiscalYear.starts_on <= target,
                FiscalYear.ends_on >= target,
            )
        )

    def default_period(self, org_id: int, target: date) -> tuple[date, date]:
        fy = self.current_fiscal_year(org_id, target)
        if fy is not None:
            return fy.starts_on, fy.ends_on
        return date(target.year, 1, 1), date(target.year, 12, 31)

    # --- reports ----------------------------------------------------------

    def trial_balance(self, org_id: int, as_of: date) -> dict:
        lines = []
        total_debit = total_credit = _ZERO
        for _id, code, name, atype, debit, credit in self._account_rows(org_id, end=as_of):
            net = debit - credit
            if net == _ZERO:
                continue
            row_debit = net if net > _ZERO else _ZERO
            row_credit = -net if net < _ZERO else _ZERO
            total_debit += row_debit
            total_credit += row_credit
            lines.append(
                {
                    "account_id": _id,
                    "code": code,
                    "name": name,
                    "account_type": atype,
                    "debit": row_debit,
                    "credit": row_credit,
                }
            )
        return {
            "as_of": as_of,
            "lines": lines,
            "total_debit": total_debit,
            "total_credit": total_credit,
            "balanced": total_debit == total_credit,
        }

    def profit_and_loss(self, org_id: int, start: date, end: date) -> dict:
        income, cogs, operating = [], [], []
        for _id, code, name, atype, debit, credit in self._account_rows(
            org_id, start=start, end=end
        ):
            if atype == "income":
                amount = credit - debit
                bucket = income
            elif atype == "expense":
                amount = debit - credit
                bucket = cogs if code.startswith("51") else operating
            else:
                continue
            if amount == _ZERO:
                continue
            bucket.append({"account_id": _id, "code": code, "name": name, "amount": amount})

        total_income = sum((r["amount"] for r in income), _ZERO)
        total_cogs = sum((r["amount"] for r in cogs), _ZERO)
        total_operating = sum((r["amount"] for r in operating), _ZERO)
        gross_profit = total_income - total_cogs
        net_profit = gross_profit - total_operating
        return {
            "from_date": start,
            "to_date": end,
            "income": income,
            "cost_of_sales": cogs,
            "operating_expenses": operating,
            "total_income": total_income,
            "total_cost_of_sales": total_cogs,
            "gross_profit": gross_profit,
            "total_operating_expenses": total_operating,
            "net_profit": net_profit,
        }

    def balance_sheet(self, org_id: int, as_of: date) -> dict:
        assets, liabilities, equity = [], [], []
        earnings = _ZERO
        for _id, code, name, atype, debit, credit in self._account_rows(org_id, end=as_of):
            if atype == "asset":
                balance = debit - credit
                bucket = assets
            elif atype == "liability":
                balance = credit - debit
                bucket = liabilities
            elif atype == "equity":
                balance = credit - debit
                bucket = equity
            else:  # income / expense accumulate into current-period earnings
                earnings += credit - debit
                continue
            if balance == _ZERO:
                continue
            bucket.append({"account_id": _id, "code": code, "name": name, "amount": balance})

        if earnings != _ZERO:
            equity.append(
                {"account_id": None, "code": None, "name": "Current Period Earnings", "amount": earnings}
            )
        total_assets = sum((r["amount"] for r in assets), _ZERO)
        total_liabilities = sum((r["amount"] for r in liabilities), _ZERO)
        total_equity = sum((r["amount"] for r in equity), _ZERO)
        return {
            "as_of": as_of,
            "assets": assets,
            "liabilities": liabilities,
            "equity": equity,
            "total_assets": total_assets,
            "total_liabilities": total_liabilities,
            "total_equity": total_equity,
            "total_liabilities_and_equity": total_liabilities + total_equity,
            "balanced": total_assets == total_liabilities + total_equity,
        }

    def general_ledger(self, org_id: int, account_id: int, start: date, end: date) -> dict:
        account = self.db.scalar(
            select(Account).where(Account.id == account_id, Account.org_id == org_id)
        )
        if account is None:
            raise NotFoundError("Account not found")

        opening = self.db.scalar(
            select(
                func.coalesce(func.sum(LedgerEntry.debit), 0)
                - func.coalesce(func.sum(LedgerEntry.credit), 0)
            ).where(
                LedgerEntry.org_id == org_id,
                LedgerEntry.account_id == account_id,
                LedgerEntry.posting_date < start,
            )
        ) or _ZERO

        entries = self.db.scalars(
            select(LedgerEntry)
            .where(
                LedgerEntry.org_id == org_id,
                LedgerEntry.account_id == account_id,
                LedgerEntry.posting_date >= start,
                LedgerEntry.posting_date <= end,
            )
            .order_by(LedgerEntry.posting_date, LedgerEntry.id)
        )
        running = opening
        rows = []
        for entry in entries:
            running += entry.debit - entry.credit
            rows.append(
                {
                    "id": entry.id,
                    "posting_date": entry.posting_date,
                    "voucher_type": entry.voucher_type,
                    "number": entry.number,
                    "description": entry.description,
                    "debit": entry.debit,
                    "credit": entry.credit,
                    "balance": running,
                }
            )
        return {
            "account_id": account.id,
            "account_code": account.code,
            "account_name": account.name,
            "from_date": start,
            "to_date": end,
            "opening_balance": opening,
            "closing_balance": running,
            "rows": rows,
        }
