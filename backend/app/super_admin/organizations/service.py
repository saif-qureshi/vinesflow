from __future__ import annotations

from sqlalchemy import func, or_, select
from sqlalchemy.orm import Session, joinedload

from app.core.crypto import encrypt_secret
from app.core.exceptions import BadRequestError, ConflictError, NotFoundError
from app.core.security import hash_password
from app.core.storage import belongs_to_org
from app.modules.auth.service import AuthService
from app.modules.orgs.models import Membership, Organization
from app.modules.orgs.service import OrgService
from app.modules.users.models import User
from app.super_admin.organizations.schemas import (
    SuperAdminOrganizationDetail,
    SuperAdminOrganizationMember,
    SuperAdminOrganizationOnboard,
    SuperAdminOrganizationOwnerPasswordResult,
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

    def get(self, org_id: int) -> SuperAdminOrganizationDetail:
        org = self.db.get(Organization, org_id)
        if org is None:
            raise NotFoundError("Organization not found")
        return self._detail(org)

    def _detail(self, org: Organization) -> SuperAdminOrganizationDetail:
        memberships = self.db.scalars(
            select(Membership)
            .where(Membership.org_id == org.id)
            .options(joinedload(Membership.user), joinedload(Membership.role))
            .order_by(Membership.is_owner.desc(), Membership.created_at, Membership.id)
        ).all()
        members = [
            SuperAdminOrganizationMember(
                membership_id=membership.id,
                user_id=membership.user.id,
                full_name=membership.user.full_name,
                email=membership.user.email,
                role_name=membership.role.name,
                role_slug=membership.role.slug,
                is_owner=membership.is_owner,
                is_active=membership.user.is_active,
            )
            for membership in memberships
        ]
        return SuperAdminOrganizationDetail(
            **self._read(org).model_dump(),
            ntn=org.ntn,
            strn=org.strn,
            cnic=org.cnic,
            address=org.address,
            logo_key=org.logo_key,
            logo_url=org.logo_url,
            fbr_enabled=org.fbr_enabled,
            fbr_environment=org.fbr_environment,
            fbr_province=org.fbr_province,
            fbr_sandbox_configured=org.fbr_sandbox_configured,
            fbr_production_configured=org.fbr_production_configured,
            members=members,
        )

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

    def update_owner_password(
        self, org_id: int, password: str
    ) -> SuperAdminOrganizationOwnerPasswordResult:
        if self.db.get(Organization, org_id) is None:
            raise NotFoundError("Organization not found")
        owner = self.db.scalar(
            select(User)
            .join(Membership, Membership.user_id == User.id)
            .where(Membership.org_id == org_id, Membership.is_owner.is_(True))
        )
        if owner is None:
            raise NotFoundError("Organization owner not found")
        owner.hashed_password = hash_password(password)
        AuthService(self.db).revoke_all_for_user(owner.id)
        self.db.commit()
        return SuperAdminOrganizationOwnerPasswordResult(
            owner_email=owner.email,
            message="Owner password updated and existing sessions revoked",
        )

    def update(
        self, org_id: int, payload: SuperAdminOrganizationUpdate
    ) -> SuperAdminOrganizationDetail:
        org = self.db.get(Organization, org_id)
        if org is None:
            raise NotFoundError("Organization not found")
        org.name = payload.name
        org.currency = payload.currency.upper()
        org.country = payload.country.upper()
        org.industry = payload.industry or None
        org.ntn = payload.ntn.strip() if payload.ntn and payload.ntn.strip() else None
        org.strn = payload.strn.strip() if payload.strn and payload.strn.strip() else None
        org.cnic = payload.cnic.strip() if payload.cnic and payload.cnic.strip() else None
        if payload.address is None:
            org.address = None
        else:
            address = payload.address.model_dump()
            org.address = address if any(address.values()) else None
        logo_key = payload.logo_key.strip() if payload.logo_key else ""
        if logo_key and not belongs_to_org(logo_key, org.id):
            raise BadRequestError("Invalid logo reference")
        org.logo_key = logo_key or None
        if payload.fbr_enabled is not None:
            org.fbr_enabled = payload.fbr_enabled
        if payload.fbr_environment is not None:
            org.fbr_environment = payload.fbr_environment
        if payload.fbr_province is not None:
            org.fbr_province = payload.fbr_province.strip() or None
        if payload.fbr_sandbox_token and payload.fbr_sandbox_token.strip():
            org.fbr_sandbox_token = encrypt_secret(payload.fbr_sandbox_token.strip())
        if payload.fbr_production_token and payload.fbr_production_token.strip():
            org.fbr_production_token = encrypt_secret(payload.fbr_production_token.strip())
        org.fiscal_year_start_month = payload.fiscal_year_start_month
        org.is_active = payload.is_active
        self.db.commit()
        self.db.refresh(org)
        return self._detail(org)
