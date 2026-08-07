from __future__ import annotations

from datetime import date
from decimal import Decimal
from itertools import groupby

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.core.exceptions import NotFoundError
from app.modules.accounting.accounts import cash_account_ids, configured_subtree_ids
from app.modules.accounting.enums import AccountType
from app.modules.accounting.models import Account, FiscalYear, LedgerEntry
from app.modules.parties.models import Party

_ZERO = Decimal("0")
_CREDIT_NORMAL = {AccountType.LIABILITY, AccountType.EQUITY, AccountType.INCOME}


def _sign(account_type: str) -> int:
    return -1 if account_type in _CREDIT_NORMAL else 1


def _cash_flow_bucket(account_type: str, code: str) -> str:
    """Current assets and liabilities fund the trade, so they are operating;
    what sits outside them is the business buying assets or raising money."""
    if account_type == AccountType.EQUITY:
        return "financing"
    if account_type == AccountType.ASSET and not code.startswith("11"):
        return "investing"
    if account_type == AccountType.LIABILITY and not code.startswith("21"):
        return "financing"
    return "operating"


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
        cost_of_sales = set(configured_subtree_ids(self.db, org_id, "cogs"))
        for _id, code, name, atype, debit, credit in self._account_rows(
            org_id, start=start, end=end
        ):
            if atype == "income":
                amount = credit - debit
                bucket = income
            elif atype == "expense":
                amount = debit - credit
                bucket = cogs if _id in cost_of_sales else operating
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

    def _opening_balance(
        self,
        org_id: int,
        start: date,
        *,
        account_id: int | None = None,
        party_id: int | None = None,
    ) -> Decimal:
        stmt = select(
            func.coalesce(func.sum(LedgerEntry.debit), 0)
            - func.coalesce(func.sum(LedgerEntry.credit), 0)
        ).where(LedgerEntry.org_id == org_id, LedgerEntry.posting_date < start)
        if account_id is not None:
            stmt = stmt.where(LedgerEntry.account_id == account_id)
        if party_id is not None:
            stmt = stmt.where(LedgerEntry.party_id == party_id)
        return self.db.scalar(stmt) or _ZERO

    def _entries(self, org_id: int, start: date, end: date):
        return (
            select(LedgerEntry)
            .where(
                LedgerEntry.org_id == org_id,
                LedgerEntry.posting_date >= start,
                LedgerEntry.posting_date <= end,
            )
            .order_by(LedgerEntry.posting_date, LedgerEntry.id)
        )

    @staticmethod
    def _statement_rows(entries, opening: Decimal, sign: int) -> tuple[list[dict], Decimal]:
        running = opening
        rows = []
        for entry in entries:
            running += (entry.debit - entry.credit) * sign
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
        return rows, running

    def account_statement(self, org_id: int, account_id: int, start: date, end: date) -> dict:
        account = self.db.scalar(
            select(Account).where(Account.id == account_id, Account.org_id == org_id)
        )
        if account is None:
            raise NotFoundError("Account not found")

        sign = _sign(account.account_type)
        opening = self._opening_balance(org_id, start, account_id=account_id) * sign
        entries = self.db.scalars(
            self._entries(org_id, start, end).where(LedgerEntry.account_id == account_id)
        )
        rows, closing = self._statement_rows(entries, opening, sign)
        return {
            "account_id": account.id,
            "account_code": account.code,
            "account_name": account.name,
            "from_date": start,
            "to_date": end,
            "opening_balance": opening,
            "closing_balance": closing,
            "rows": rows,
        }

    def party_statement(self, org_id: int, party_id: int, start: date, end: date) -> dict:
        party = self.db.scalar(select(Party).where(Party.id == party_id, Party.org_id == org_id))
        if party is None:
            raise NotFoundError("Party not found")

        # Only the receivable/payable leg of a voucher carries the party, so filtering
        # on it alone yields what the party owes — never their revenue or tax lines.
        sign = -1 if party.is_vendor and not party.is_customer else 1
        opening = self._opening_balance(org_id, start, party_id=party_id) * sign
        entries = self.db.scalars(
            self._entries(org_id, start, end).where(LedgerEntry.party_id == party_id)
        )
        rows, closing = self._statement_rows(entries, opening, sign)
        return {
            "party_id": party.id,
            "party_name": party.name,
            "from_date": start,
            "to_date": end,
            "opening_balance": opening,
            "closing_balance": closing,
            "rows": rows,
        }

    def cash_book(self, org_id: int, start: date, end: date) -> dict:
        """Each cash and bank account day by day: what it opened with, what came
        in and went out, what it closed with."""
        cash_ids = cash_account_ids(self.db, org_id)
        if not cash_ids:
            return {"from_date": start, "to_date": end, "accounts": []}

        openings = dict(
            self.db.execute(
                select(
                    LedgerEntry.account_id,
                    func.coalesce(func.sum(LedgerEntry.debit - LedgerEntry.credit), 0),
                )
                .where(
                    LedgerEntry.org_id == org_id,
                    LedgerEntry.account_id.in_(cash_ids),
                    LedgerEntry.posting_date < start,
                )
                .group_by(LedgerEntry.account_id)
            ).all()
        )
        daily = self.db.execute(
            select(
                Account.id,
                Account.code,
                Account.name,
                LedgerEntry.posting_date,
                func.coalesce(func.sum(LedgerEntry.debit), 0),
                func.coalesce(func.sum(LedgerEntry.credit), 0),
            )
            .join(Account, Account.id == LedgerEntry.account_id)
            .where(
                LedgerEntry.org_id == org_id,
                LedgerEntry.account_id.in_(cash_ids),
                LedgerEntry.posting_date >= start,
                LedgerEntry.posting_date <= end,
            )
            .group_by(Account.id, LedgerEntry.posting_date)
            .order_by(Account.code, LedgerEntry.posting_date)
        ).all()

        seen = {row[0] for row in daily}
        accounts = []
        for account_id, group in groupby(daily, key=lambda row: row[0]):
            days = list(group)
            _, code, name, *_ = days[0]
            running = openings.get(account_id, _ZERO)
            opening = running
            rows = []
            received = paid = _ZERO
            for _, _, _, day, debit, credit in days:
                running += debit - credit
                received += debit
                paid += credit
                rows.append(
                    {
                        "date": day,
                        "opening": running - debit + credit,
                        "received": debit,
                        "paid": credit,
                        "closing": running,
                    }
                )
            accounts.append(
                {
                    "account_id": account_id,
                    "code": code,
                    "name": name,
                    "opening": opening,
                    "received": received,
                    "paid": paid,
                    "closing": running,
                    "rows": rows,
                }
            )

        for account_id, code, name in self.db.execute(
            select(Account.id, Account.code, Account.name)
            .where(Account.id.in_(cash_ids), Account.is_postable.is_(True))
            .order_by(Account.code)
        ).all():
            if account_id in seen:
                continue
            balance = openings.get(account_id, _ZERO)
            accounts.append(
                {
                    "account_id": account_id,
                    "code": code,
                    "name": name,
                    "opening": balance,
                    "received": _ZERO,
                    "paid": _ZERO,
                    "closing": balance,
                    "rows": [],
                }
            )
        accounts.sort(key=lambda a: a["code"])
        return {"from_date": start, "to_date": end, "accounts": accounts}

    def cash_flow(self, org_id: int, start: date, end: date) -> dict:
        """Direct method: every voucher that moved cash, classified by what it
        moved cash *for* — the non-cash side of the same voucher."""
        cash_ids = cash_account_ids(self.db, org_id)
        empty = {
            "from_date": start,
            "to_date": end,
            "opening_cash": _ZERO,
            "operating": [],
            "investing": [],
            "financing": [],
            "total_operating": _ZERO,
            "total_investing": _ZERO,
            "total_financing": _ZERO,
            "net_change": _ZERO,
            "closing_cash": _ZERO,
        }
        if not cash_ids:
            return empty

        opening = self.db.scalar(
            select(func.coalesce(func.sum(LedgerEntry.debit - LedgerEntry.credit), 0)).where(
                LedgerEntry.org_id == org_id,
                LedgerEntry.account_id.in_(cash_ids),
                LedgerEntry.posting_date < start,
            )
        ) or _ZERO

        moved = select(LedgerEntry.voucher_id).where(
            LedgerEntry.org_id == org_id,
            LedgerEntry.account_id.in_(cash_ids),
            LedgerEntry.posting_date >= start,
            LedgerEntry.posting_date <= end,
        )
        # The voucher balances, so its non-cash lines net to exactly the cash it moved.
        counterparts = self.db.execute(
            select(
                Account.id,
                Account.code,
                Account.name,
                Account.account_type,
                func.coalesce(func.sum(LedgerEntry.credit - LedgerEntry.debit), 0),
            )
            .join(Account, Account.id == LedgerEntry.account_id)
            .where(
                LedgerEntry.org_id == org_id,
                LedgerEntry.voucher_id.in_(moved),
                LedgerEntry.account_id.not_in(cash_ids),
            )
            .group_by(Account.id)
            .order_by(Account.code)
        ).all()

        buckets: dict[str, list[dict]] = {"operating": [], "investing": [], "financing": []}
        for account_id, code, name, account_type, amount in counterparts:
            if amount == _ZERO:
                continue
            buckets[_cash_flow_bucket(account_type, code)].append(
                {"account_id": account_id, "code": code, "name": name, "amount": amount}
            )

        totals = {
            key: sum((row["amount"] for row in rows), _ZERO) for key, rows in buckets.items()
        }
        net = totals["operating"] + totals["investing"] + totals["financing"]
        return {
            "from_date": start,
            "to_date": end,
            "opening_cash": opening,
            "operating": buckets["operating"],
            "investing": buckets["investing"],
            "financing": buckets["financing"],
            "total_operating": totals["operating"],
            "total_investing": totals["investing"],
            "total_financing": totals["financing"],
            "net_change": net,
            "closing_cash": opening + net,
        }

    def general_ledger(self, org_id: int, start: date, end: date) -> dict:
        openings = dict(
            self.db.execute(
                select(
                    LedgerEntry.account_id,
                    func.coalesce(func.sum(LedgerEntry.debit), 0)
                    - func.coalesce(func.sum(LedgerEntry.credit), 0),
                )
                .where(LedgerEntry.org_id == org_id, LedgerEntry.posting_date < start)
                .group_by(LedgerEntry.account_id)
            ).all()
        )
        posted = self.db.execute(
            select(LedgerEntry, Account)
            .join(Account, Account.id == LedgerEntry.account_id)
            .where(
                LedgerEntry.org_id == org_id,
                LedgerEntry.posting_date >= start,
                LedgerEntry.posting_date <= end,
            )
            .order_by(Account.code, LedgerEntry.posting_date, LedgerEntry.id)
        ).all()

        accounts = []
        total_debit = total_credit = _ZERO
        for _account_id, group in groupby(posted, key=lambda row: row[1].id):
            entries = list(group)
            account = entries[0][1]
            sign = _sign(account.account_type)
            opening = openings.get(account.id, _ZERO) * sign
            rows, closing = self._statement_rows((e[0] for e in entries), opening, sign)
            total_debit += sum((r["debit"] for r in rows), _ZERO)
            total_credit += sum((r["credit"] for r in rows), _ZERO)
            accounts.append(
                {
                    "account_id": account.id,
                    "account_code": account.code,
                    "account_name": account.name,
                    "opening_balance": opening,
                    "closing_balance": closing,
                    "rows": rows,
                }
            )
        return {
            "from_date": start,
            "to_date": end,
            "accounts": accounts,
            "total_debit": total_debit,
            "total_credit": total_credit,
        }
