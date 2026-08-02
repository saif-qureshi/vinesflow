from __future__ import annotations

from sqlalchemy import func, or_, select
from sqlalchemy.orm import Session

from app.core.exceptions import ConflictError, NotFoundError
from app.core.security import hash_password
from app.modules.orgs.models import Membership, Organization
from app.modules.orgs.service import OrgService
from app.modules.users.models import User
from app.super_admin.organizations.schemas import (
    SuperAdminOrganizationOnboard,
    SuperAdminOrganizationPage,
    SuperAdminOrganizationRead,
    SuperAdminOrganizationUpdate,
)


class SuperAdminOrganizationService:
    def __init__(self, db: Session) -> None:
        self.db = db

    def _read(self, org: Organization) -> SuperAdminOrganizationRead:
        owner = self.db.execute(
            select(User.full_name, User.email)
            .join(Membership, Membership.user_id == User.id)
            .where(Membership.org_id == org.id, Membership.is_owner.is_(True))
        ).first()
        member_count = (
            self.db.scalar(
                select(func.count()).select_from(Membership).where(Membership.org_id == org.id)
            )
            or 0
        )
        return SuperAdminOrganizationRead(
            id=org.id,
            name=org.name,
            slug=org.slug,
            currency=org.currency,
            country=org.country,
            industry=org.industry,
            is_active=org.is_active,
            owner_name=owner.full_name if owner else None,
            owner_email=owner.email if owner else "",
            member_count=member_count,
            fiscal_year_start_month=org.fiscal_year_start_month,
            created_at=org.created_at,
        )

    def get(self, org_id: int) -> SuperAdminOrganizationRead:
        org = self.db.get(Organization, org_id)
        if org is None:
            raise NotFoundError("Organization not found")
        return self._read(org)

    def list(self, *, search: str | None, page: int, page_size: int) -> SuperAdminOrganizationPage:
        filters = []
        if search and search.strip():
            like = f"%{search.strip()}%"
            filters.append(or_(Organization.name.ilike(like), Organization.slug.ilike(like)))
        total_stmt = select(func.count()).select_from(Organization)
        list_stmt = select(Organization)
        if filters:
            total_stmt = total_stmt.where(*filters)
            list_stmt = list_stmt.where(*filters)
        total = self.db.scalar(total_stmt) or 0
        organizations = self.db.scalars(
            list_stmt.order_by(Organization.created_at.desc(), Organization.id.desc())
            .offset((page - 1) * page_size)
            .limit(page_size)
        ).all()
        return SuperAdminOrganizationPage(
            items=[self._read(org) for org in organizations],
            total=total,
            page=page,
            page_size=page_size,
        )

    def onboard(self, payload: SuperAdminOrganizationOnboard) -> SuperAdminOrganizationRead:
        email = payload.owner_email.lower()
        if self.db.scalar(select(User.id).where(User.email == email)) is not None:
            raise ConflictError("Owner email is already registered", code="email_taken")
        owner = User(
            email=email,
            full_name=payload.owner_full_name,
            hashed_password=hash_password(payload.owner_password),
        )
        self.db.add(owner)
        self.db.flush()
        org = OrgService(self.db).create_org_with_owner(
            owner=owner,
            name=payload.name,
            currency=payload.currency.upper(),
            fiscal_year_start_month=payload.fiscal_year_start_month,
        )
        org.country = payload.country.upper()
        org.industry = payload.industry
        self.db.commit()
        self.db.refresh(org)
        return self._read(org)

    def set_status(self, org_id: int, is_active: bool) -> SuperAdminOrganizationRead:
        org = self.db.get(Organization, org_id)
        if org is None:
            raise NotFoundError("Organization not found")
        org.is_active = is_active
        self.db.commit()
        self.db.refresh(org)
        return self._read(org)

    def update(
        self, org_id: int, payload: SuperAdminOrganizationUpdate
    ) -> SuperAdminOrganizationRead:
        org = self.db.get(Organization, org_id)
        if org is None:
            raise NotFoundError("Organization not found")
        org.name = payload.name
        org.currency = payload.currency.upper()
        org.country = payload.country.upper()
        org.industry = payload.industry or None
        org.fiscal_year_start_month = payload.fiscal_year_start_month
        org.is_active = payload.is_active
        self.db.commit()
        self.db.refresh(org)
        return self._read(org)
