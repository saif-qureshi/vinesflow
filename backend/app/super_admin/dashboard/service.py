from datetime import UTC, date, datetime, time, timedelta

from sqlalchemy import and_, func, or_, select
from sqlalchemy.orm import Session

from app.modules.auth.models import RefreshSession
from app.modules.documents.enums import DocumentStatus, DocumentType
from app.modules.documents.models import Document
from app.modules.fbr.models import FbrSubmissionAttempt
from app.modules.orgs.models import Membership, Organization
from app.modules.users.models import User
from app.super_admin.dashboard.schemas import (
    SuperAdminDashboardActivityPoint,
    SuperAdminDashboardFbrInvoicePoint,
    SuperAdminDashboardOrganization,
    SuperAdminDashboardRead,
)


class SuperAdminDashboardService:
    def __init__(self, db: Session) -> None:
        self.db = db

    def read(self) -> SuperAdminDashboardRead:
        organizations = self.db.scalar(select(func.count()).select_from(Organization)) or 0
        active = (
            self.db.scalar(
                select(func.count())
                .select_from(Organization)
                .where(Organization.is_active.is_(True))
            )
            or 0
        )
        users = self.db.scalar(select(func.count()).select_from(User)) or 0
        created_since = datetime.now(UTC) - timedelta(days=30)
        new_organizations = (
            self.db.scalar(
                select(func.count())
                .select_from(Organization)
                .where(Organization.created_at >= created_since)
            )
            or 0
        )
        fbr_enabled = (
            self.db.scalar(
                select(func.count())
                .select_from(Organization)
                .where(Organization.fbr_enabled.is_(True))
            )
            or 0
        )
        missing_tax_identity = and_(
            or_(Organization.ntn.is_(None), Organization.ntn == ""),
            or_(Organization.strn.is_(None), Organization.strn == ""),
            or_(Organization.cnic.is_(None), Organization.cnic == ""),
        )
        tax_identity = (
            self.db.scalar(
                select(func.count()).select_from(Organization).where(~missing_tax_identity)
            )
            or 0
        )
        missing_active_token = or_(
            and_(
                Organization.fbr_environment == "sandbox",
                or_(
                    Organization.fbr_sandbox_token.is_(None),
                    Organization.fbr_sandbox_token == "",
                ),
            ),
            and_(
                Organization.fbr_environment == "production",
                or_(
                    Organization.fbr_production_token.is_(None),
                    Organization.fbr_production_token == "",
                ),
            ),
        )
        fbr_issues = (
            self.db.scalar(
                select(func.count())
                .select_from(Organization)
                .where(Organization.fbr_enabled.is_(True), missing_active_token)
            )
            or 0
        )
        recent = self.db.scalars(
            select(Organization)
            .order_by(Organization.created_at.desc(), Organization.id.desc())
            .limit(6)
        ).all()
        return SuperAdminDashboardRead(
            organizations=organizations,
            active_organizations=active,
            inactive_organizations=organizations - active,
            organization_users=users,
            new_organizations_30d=new_organizations,
            fbr_enabled_organizations=fbr_enabled,
            tax_identity_organizations=tax_identity,
            fbr_configuration_issues=fbr_issues,
            recent_organizations=[self._organization(org) for org in recent],
            activity_14d=self._activity(),
            fbr_invoice_activity_14d=self._fbr_invoice_activity(),
        )

    def _activity(self) -> list[SuperAdminDashboardActivityPoint]:
        today = datetime.now(UTC).date()
        first_day = today - timedelta(days=13)
        since = datetime.combine(first_day, time.min, tzinfo=UTC)
        login_rows = self.db.execute(
            select(
                func.date(RefreshSession.created_at),
                func.count(func.distinct(RefreshSession.family_id)),
            )
            .where(RefreshSession.created_at >= since)
            .group_by(func.date(RefreshSession.created_at))
        ).all()
        organization_rows = self.db.execute(
            select(func.date(Organization.created_at), func.count())
            .where(Organization.created_at >= since)
            .group_by(func.date(Organization.created_at))
        ).all()
        login_counts = {self._as_date(day): count for day, count in login_rows}
        organization_counts = {self._as_date(day): count for day, count in organization_rows}
        return [
            SuperAdminDashboardActivityPoint(
                date=day.isoformat(),
                customer_logins=login_counts.get(day, 0),
                organizations_created=organization_counts.get(day, 0),
            )
            for day in (first_day + timedelta(days=offset) for offset in range(14))
        ]

    def _fbr_invoice_activity(self) -> list[SuperAdminDashboardFbrInvoicePoint]:
        today = datetime.now(UTC).date()
        first_day = today - timedelta(days=13)
        since = datetime.combine(first_day, time.min, tzinfo=UTC)
        attempt_rows = self.db.execute(
            select(
                func.date(FbrSubmissionAttempt.created_at),
                FbrSubmissionAttempt.status,
                func.count(),
            )
            .join(Document, Document.id == FbrSubmissionAttempt.document_id)
            .where(
                FbrSubmissionAttempt.created_at >= since,
                Document.type == DocumentType.INVOICE,
            )
            .group_by(func.date(FbrSubmissionAttempt.created_at), FbrSubmissionAttempt.status)
        ).all()
        failed_attempt = (
            select(FbrSubmissionAttempt.id)
            .where(
                FbrSubmissionAttempt.document_id == Document.id,
                FbrSubmissionAttempt.status == "failed",
            )
            .exists()
        )
        draft_rows = self.db.execute(
            select(func.date(Document.created_at), func.count())
            .join(Organization, Organization.id == Document.org_id)
            .where(
                Document.created_at >= since,
                Document.type == DocumentType.INVOICE,
                Document.status == DocumentStatus.DRAFT,
                Organization.fbr_enabled.is_(True),
                ~failed_attempt,
            )
            .group_by(func.date(Document.created_at))
        ).all()
        attempts: dict[date, dict[str, int]] = {}
        for day, status, count in attempt_rows:
            attempts.setdefault(self._as_date(day), {})[status] = count
        drafts = {self._as_date(day): count for day, count in draft_rows}
        return [
            SuperAdminDashboardFbrInvoicePoint(
                date=day.isoformat(),
                submitted=attempts.get(day, {}).get("submitted", 0),
                draft=drafts.get(day, 0),
                failed=attempts.get(day, {}).get("failed", 0),
            )
            for day in (first_day + timedelta(days=offset) for offset in range(14))
        ]

    @staticmethod
    def _as_date(value: date | datetime) -> date:
        return value.date() if isinstance(value, datetime) else value

    def _organization(self, org: Organization) -> SuperAdminDashboardOrganization:
        owner_email = self.db.scalar(
            select(User.email)
            .join(Membership, Membership.user_id == User.id)
            .where(Membership.org_id == org.id, Membership.is_owner.is_(True))
        )
        member_count = (
            self.db.scalar(
                select(func.count()).select_from(Membership).where(Membership.org_id == org.id)
            )
            or 0
        )
        active_token = (
            org.fbr_sandbox_token if org.fbr_environment == "sandbox" else org.fbr_production_token
        )
        return SuperAdminDashboardOrganization(
            id=org.id,
            name=org.name,
            slug=org.slug,
            is_active=org.is_active,
            owner_email=owner_email or "",
            member_count=member_count,
            tax_identity_configured=bool(org.cnic or org.ntn or org.strn),
            fbr_enabled=org.fbr_enabled,
            fbr_ready=bool(org.fbr_enabled and active_token),
            created_at=org.created_at,
        )
