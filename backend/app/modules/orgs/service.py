from __future__ import annotations

from sqlalchemy import select
from sqlalchemy.orm import Session, joinedload

from app.core.crypto import encrypt_secret
from app.core.exceptions import ConflictError, NotFoundError
from app.core.utils import slugify
from app.modules.accounting.setup import AccountingSetupService
from app.modules.activities.service import ActivityService
from app.modules.documents.service import DocumentService
from app.modules.inventory.service import InventoryService
from app.modules.locations.service import LocationService
from app.modules.orgs.models import Membership, Organization
from app.modules.orgs.schemas import MemberAdd, MemberUpdate, OrgCreate, OrgUpdate
from app.modules.rbac.constants import ALL_PERMISSION_CODES, OWNER_ROLE_SLUG
from app.modules.rbac.models import Role
from app.modules.rbac.service import RbacService
from app.modules.settings.service import SettingsService
from app.modules.uoms.service import UomService
from app.modules.users.models import User

_BRANDING_FIELDS = {"theme", "accent_color", "keep_branding", "logo_url"}
_FBR_TOKEN_FIELDS = {"fbr_sandbox_token", "fbr_production_token"}


class OrgService:
    def __init__(self, db: Session) -> None:
        self.db = db
        self.rbac = RbacService(db)
        self.activity = ActivityService(db)

    # --- Creation ---------------------------------------------------------

    def _unique_slug(self, base: str) -> str:
        slug = slugify(base)
        candidate = slug
        i = 2
        while (
            self.db.scalar(select(Organization.id).where(Organization.slug == candidate)) is not None
        ):
            candidate = f"{slug}-{i}"
            i += 1
        return candidate

    def create_org_with_owner(
        self,
        *,
        owner: User,
        name: str,
        slug: str | None = None,
        currency: str = "PKR",
        fiscal_year_start_month: int = 7,
    ) -> Organization:
        """Create an org, seed its default roles, and make `owner` its super admin."""
        org = Organization(
            name=name,
            slug=self._unique_slug(slug or name),
            currency=currency,
            fiscal_year_start_month=fiscal_year_start_month,
        )
        self.db.add(org)
        self.db.flush()

        roles = self.rbac.create_default_roles(org.id)
        owner_role = roles[OWNER_ROLE_SLUG]
        self.db.add(
            Membership(user_id=owner.id, org_id=org.id, role_id=owner_role.id, is_owner=True)
        )
        UomService(self.db).seed_defaults(org.id)
        LocationService(self.db).seed_default(org.id)
        InventoryService(self.db).seed_reasons(org.id)
        DocumentService(self.db).seed_tax_rates(org.id)
        SettingsService(self.db).seed_numbering(org.id)
        AccountingSetupService(self.db).ensure_setup(org.id, fiscal_year_start_month)
        self.db.flush()
        return org

    # --- Organizations ----------------------------------------------------

    def list_user_memberships(self, user_id: int) -> list[Membership]:
        return list(
            self.db.scalars(
                select(Membership)
                .where(Membership.user_id == user_id)
                .options(joinedload(Membership.organization), joinedload(Membership.role))
                .order_by(Membership.created_at)
            ).all()
        )

    def create_org(self, *, owner: User, payload: OrgCreate) -> Organization:
        org = self.create_org_with_owner(
            owner=owner,
            name=payload.name,
            slug=payload.slug,
            currency=payload.currency,
            fiscal_year_start_month=payload.fiscal_year_start_month,
        )
        org.industry = payload.industry
        self.db.commit()
        self.db.refresh(org)
        return org

    def update_org(self, *, membership: Membership, payload: OrgUpdate) -> Organization:
        org = membership.organization
        if payload.name is not None:
            org.name = payload.name
        if payload.currency is not None:
            org.currency = payload.currency.upper()
        if payload.industry is not None:
            org.industry = payload.industry
        if payload.country is not None:
            org.country = payload.country.upper()
        if payload.ntn is not None:
            org.ntn = payload.ntn or None
        if payload.strn is not None:
            org.strn = payload.strn or None
        if payload.cnic is not None:
            org.cnic = payload.cnic or None
        if "address" in payload.model_fields_set:
            org.address = payload.address.model_dump() if payload.address else None
        if payload.fiscal_year_start_month is not None:
            org.fiscal_year_start_month = payload.fiscal_year_start_month
        if payload.logo_url is not None:
            org.logo_url = payload.logo_url or None
        if payload.theme is not None:
            org.theme = payload.theme
        if payload.accent_color is not None:
            org.accent_color = payload.accent_color
        if payload.keep_branding is not None:
            org.keep_branding = payload.keep_branding
        if payload.fbr_enabled is not None:
            org.fbr_enabled = payload.fbr_enabled
        if payload.fbr_environment is not None:
            org.fbr_environment = payload.fbr_environment
        if payload.fbr_province is not None:
            org.fbr_province = payload.fbr_province or None
        if "fbr_sandbox_token" in payload.model_fields_set:
            org.fbr_sandbox_token = (
                encrypt_secret(payload.fbr_sandbox_token) if payload.fbr_sandbox_token else None
            )
        if "fbr_production_token" in payload.model_fields_set:
            org.fbr_production_token = (
                encrypt_secret(payload.fbr_production_token)
                if payload.fbr_production_token
                else None
            )
        changed = payload.model_fields_set - _BRANDING_FIELDS - _FBR_TOKEN_FIELDS
        if changed:
            self.activity.record(
                org.id, "updated", "organization", org.name,
                entity_id=org.id, context={"fields": sorted(changed)},
            )
        self.db.commit()
        self.db.refresh(org)
        return org

    @staticmethod
    def permissions_for(membership: Membership) -> list[str]:
        if membership.user.is_superuser or membership.is_owner:
            return sorted(ALL_PERMISSION_CODES)
        return sorted({p.code for p in membership.role.permissions})

    # --- Members ----------------------------------------------------------

    def list_members(self, org_id: int) -> list[Membership]:
        return list(
            self.db.scalars(
                select(Membership)
                .where(Membership.org_id == org_id)
                .options(joinedload(Membership.user), joinedload(Membership.role))
                .order_by(Membership.created_at)
            ).all()
        )

    def _get_org_role(self, org_id: int, role_id: int) -> Role:
        role = self.db.scalar(select(Role).where(Role.id == role_id, Role.org_id == org_id))
        if role is None:
            raise NotFoundError("Role not found")
        return role

    def _get_member(self, org_id: int, membership_id: int) -> Membership:
        member = self.db.scalar(
            select(Membership).where(Membership.id == membership_id, Membership.org_id == org_id)
        )
        if member is None:
            raise NotFoundError("Member not found")
        return member

    def add_member(self, *, org_id: int, payload: MemberAdd) -> Membership:
        role = self._get_org_role(org_id, payload.role_id)
        user = self.db.scalar(select(User).where(User.email == payload.email.lower()))
        if user is None:
            raise NotFoundError("No registered user with that email. They must sign up first.")
        if self.db.scalar(
            select(Membership).where(Membership.org_id == org_id, Membership.user_id == user.id)
        ):
            raise ConflictError("User is already a member")
        member = Membership(user_id=user.id, org_id=org_id, role_id=role.id, is_owner=False)
        self.db.add(member)
        self.db.flush()
        self.activity.record(
            org_id, "added", "member", user.email, entity_id=member.id, context={"role": role.name}
        )
        self.db.commit()
        self.db.refresh(member)
        return member

    def update_member_role(
        self, *, org_id: int, membership_id: int, payload: MemberUpdate
    ) -> Membership:
        member = self._get_member(org_id, membership_id)
        if member.is_owner:
            raise ConflictError("Cannot change the owner's role")
        role = self._get_org_role(org_id, payload.role_id)
        member.role_id = role.id
        self.activity.record(
            org_id, "updated", "member", member.user.email,
            entity_id=member.id, context={"role": role.name},
        )
        self.db.commit()
        self.db.refresh(member)
        return member

    def remove_member(self, *, org_id: int, membership_id: int) -> None:
        member = self._get_member(org_id, membership_id)
        if member.is_owner:
            raise ConflictError("Cannot remove the org owner")
        self.activity.record(org_id, "removed", "member", member.user.email, entity_id=member.id)
        self.db.delete(member)
        self.db.commit()
