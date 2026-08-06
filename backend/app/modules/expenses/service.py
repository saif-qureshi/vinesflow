from __future__ import annotations

from datetime import UTC, date, datetime
from decimal import Decimal

from sqlalchemy import or_, select
from sqlalchemy.orm import Session, joinedload

from app.core import ledger as _ledger
from app.core.exceptions import BadRequestError, NotFoundError
from app.core.pagination import paginate_cursor
from app.modules.accounting.models import Account
from app.modules.activities.service import ActivityService
from app.modules.documents.numbering import assign_number, numbering_format
from app.modules.expenses.enums import EXPENSE_PREFIX, ExpenseStatus
from app.modules.expenses.models import Expense, ExpenseLine
from app.modules.expenses.schemas import (
    ExpenseCreate,
    ExpenseLineInput,
    ExpenseListQuery,
    ExpenseUpdate,
)
from app.modules.expenses.totals import quantize as _q
from app.modules.expenses.totals import totals as _compute_totals
from app.modules.parties.models import Party

_ZERO = Decimal("0")


def _now() -> datetime:
    return datetime.now(UTC)


class ExpenseService:
    def __init__(self, db: Session) -> None:
        self.db = db
        self.activity = ActivityService(db)
        self.ledger = _ledger.ledger_poster

    def _get_account(self, org_id: int, account_id: int) -> Account:
        account = self.db.scalar(
            select(Account).where(Account.id == account_id, Account.org_id == org_id)
        )
        if account is None:
            raise NotFoundError("Account not found")
        if not account.is_postable:
            raise BadRequestError(f"{account.code} {account.name} is not a postable account")
        return account

    def _get_party(self, org_id: int, party_id: int) -> Party:
        party = self.db.scalar(select(Party).where(Party.id == party_id, Party.org_id == org_id))
        if party is None:
            raise NotFoundError("Party not found")
        return party

    def _build_lines(self, org_id: int, inputs: list[ExpenseLineInput]) -> list[ExpenseLine]:
        lines = []
        for index, line in enumerate(inputs, start=1):
            self._get_account(org_id, line.account_id)
            lines.append(
                ExpenseLine(
                    account_id=line.account_id,
                    line_no=index,
                    description=line.description,
                    amount=_q(line.amount),
                )
            )
        return lines

    @staticmethod
    def _totals(
        lines: list[ExpenseLine], tax_amount: Decimal, *, is_tax_inclusive: bool
    ) -> tuple[Decimal, Decimal, Decimal]:
        amounts = [line.amount for line in lines]
        subtotal, tax, total = _compute_totals(
            amounts, tax_amount, is_tax_inclusive=is_tax_inclusive
        )
        if subtotal < _ZERO:
            raise BadRequestError("Tax cannot exceed the expense amount")
        return subtotal, tax, total

    def create(self, org_id: int, payload: ExpenseCreate) -> Expense:
        paid_through = self._get_account(org_id, payload.paid_through_account_id)
        vendor = self._get_party(org_id, payload.vendor_id) if payload.vendor_id else None
        if payload.customer_id:
            self._get_party(org_id, payload.customer_id)
        lines = self._build_lines(org_id, payload.lines)
        subtotal, tax, total = self._totals(
            lines, payload.tax_amount, is_tax_inclusive=payload.is_tax_inclusive
        )
        expense_date = payload.expense_date or date.today()
        prefix, start, restart = numbering_format(self.db, org_id, "expense", EXPENSE_PREFIX)
        expense = Expense(
            org_id=org_id,
            status=ExpenseStatus.DRAFT,
            expense_date=expense_date,
            paid_through_account_id=paid_through.id,
            vendor_id=vendor.id if vendor else None,
            vendor_name=vendor.name if vendor else None,
            customer_id=payload.customer_id,
            is_tax_inclusive=payload.is_tax_inclusive,
            reference_no=payload.reference_no,
            notes=payload.notes,
            subtotal=subtotal,
            tax_amount=tax,
            total=total,
            lines=lines,
        )
        assign_number(
            self.db,
            expense,
            Expense.number,
            prefix,
            start,
            restart,
            expense_date.year,
            Expense.org_id == org_id,
        )
        self.activity.record(org_id, "created", "expense", expense.number, entity_id=expense.id)
        self.db.commit()
        self.db.refresh(expense)
        return expense

    def get(self, org_id: int, expense_id: int) -> Expense:
        expense = self.db.scalar(
            select(Expense)
            .where(Expense.id == expense_id, Expense.org_id == org_id)
            .options(joinedload(Expense.vendor))
        )
        if expense is None:
            raise NotFoundError("Expense not found")
        return expense

    def list(self, org_id: int, query: ExpenseListQuery):
        stmt = select(Expense).where(Expense.org_id == org_id)
        if query.status:
            stmt = stmt.where(Expense.status == query.status)
        if query.vendor_id is not None:
            stmt = stmt.where(Expense.vendor_id == query.vendor_id)
        if query.search:
            like = f"%{query.search.strip()}%"
            stmt = stmt.where(
                or_(
                    Expense.number.ilike(like),
                    Expense.vendor_name.ilike(like),
                    Expense.reference_no.ilike(like),
                )
            )
        return paginate_cursor(self.db, stmt, Expense.id, query)

    def update(self, org_id: int, expense_id: int, payload: ExpenseUpdate) -> Expense:
        expense = self.get(org_id, expense_id)
        if expense.status != ExpenseStatus.DRAFT:
            raise BadRequestError("Only draft expenses can be edited")
        fields = payload.model_fields_set
        if "paid_through_account_id" in fields and payload.paid_through_account_id is not None:
            expense.paid_through_account_id = self._get_account(
                org_id, payload.paid_through_account_id
            ).id
        if "vendor_id" in fields:
            vendor = self._get_party(org_id, payload.vendor_id) if payload.vendor_id else None
            expense.vendor_id = vendor.id if vendor else None
            expense.vendor_name = vendor.name if vendor else None
        if "customer_id" in fields:
            if payload.customer_id:
                self._get_party(org_id, payload.customer_id)
            expense.customer_id = payload.customer_id
        for field in ("expense_date", "is_tax_inclusive", "reference_no", "notes"):
            if field in fields and getattr(payload, field) is not None:
                setattr(expense, field, getattr(payload, field))
        if payload.lines is not None:
            expense.lines = self._build_lines(org_id, payload.lines)
        tax = payload.tax_amount if payload.tax_amount is not None else expense.tax_amount
        expense.subtotal, expense.tax_amount, expense.total = self._totals(
            expense.lines, tax, is_tax_inclusive=expense.is_tax_inclusive
        )
        self.activity.record(org_id, "updated", "expense", expense.number, entity_id=expense.id)
        self.db.commit()
        self.db.refresh(expense)
        return expense

    def submit(self, org_id: int, expense_id: int) -> Expense:
        expense = self.get(org_id, expense_id)
        if expense.status != ExpenseStatus.DRAFT:
            raise BadRequestError("Only draft expenses can be submitted")
        self.ledger.post_expense(self.db, expense)
        expense.status = ExpenseStatus.SUBMITTED
        expense.submitted_at = _now()
        expense.submitted_by_id = self.db.info.get("actor_id")
        self.activity.record(org_id, "submitted", "expense", expense.number, entity_id=expense.id)
        self.db.commit()
        self.db.refresh(expense)
        return expense

    def cancel(self, org_id: int, expense_id: int) -> Expense:
        expense = self.get(org_id, expense_id)
        if expense.status == ExpenseStatus.CANCELLED:
            raise BadRequestError("Expense is already cancelled")
        if expense.status == ExpenseStatus.SUBMITTED:
            self.ledger.reverse_expense(self.db, expense)
        expense.status = ExpenseStatus.CANCELLED
        expense.cancelled_at = _now()
        expense.cancelled_by_id = self.db.info.get("actor_id")
        self.activity.record(org_id, "cancelled", "expense", expense.number, entity_id=expense.id)
        self.db.commit()
        self.db.refresh(expense)
        return expense

    def delete(self, org_id: int, expense_id: int) -> None:
        expense = self.get(org_id, expense_id)
        if expense.status != ExpenseStatus.DRAFT:
            raise BadRequestError("Only draft expenses can be deleted")
        self.activity.record(org_id, "deleted", "expense", expense.number, entity_id=expense.id)
        self.db.delete(expense)
        self.db.commit()
