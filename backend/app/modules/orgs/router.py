from __future__ import annotations

from fastapi import APIRouter, Depends, status

from app.api.deps import CurrentMembership, CurrentUser, require_permission
from app.core.config import settings
from app.core.container import Provide
from app.core.exceptions import ForbiddenError
from app.core.responses import EnvelopeRoute
from app.modules.orgs.models import Membership, Organization
from app.modules.orgs.schemas import (
    MemberAdd,
    MemberRead,
    MemberUpdate,
    OrgCreate,
    OrgMembership,
    OrgRead,
    OrgUpdate,
)
from app.modules.orgs.service import OrgService

router = APIRouter(prefix="/orgs", tags=["orgs"], route_class=EnvelopeRoute)

OrgSvc = Depends(Provide(OrgService))


@router.get("", response_model=list[OrgMembership])
def list_my_orgs(current_user: CurrentUser, orgs: OrgService = OrgSvc) -> list[Membership]:
    return orgs.list_user_memberships(current_user.id)


@router.post("", response_model=OrgRead, status_code=status.HTTP_201_CREATED)
def create_org(payload: OrgCreate, current_user: CurrentUser, orgs: OrgService = OrgSvc) -> Organization:
    if not settings.SELF_SERVICE_ORG_CREATION_ENABLED:
        raise ForbiddenError("Organizations are provisioned by a super administrator")
    return orgs.create_org(owner=current_user, payload=payload)


@router.get("/current", response_model=OrgRead)
def get_current_org(membership: CurrentMembership) -> Organization:
    return membership.organization


@router.get("/current/my-permissions", response_model=list[str])
def my_permissions(membership: CurrentMembership) -> list[str]:
    return OrgService.permissions_for(membership)


@router.patch("/current", response_model=OrgRead)
def update_current_org(
    payload: OrgUpdate,
    membership: Membership = Depends(require_permission("orgs:update")),
    orgs: OrgService = OrgSvc,
) -> Organization:
    return orgs.update_org(membership=membership, payload=payload)


@router.get("/current/members", response_model=list[MemberRead])
def list_members(
    membership: Membership = Depends(require_permission("users:read")),
    orgs: OrgService = OrgSvc,
) -> list[Membership]:
    return orgs.list_members(membership.org_id)


@router.post("/current/members", response_model=MemberRead, status_code=status.HTTP_201_CREATED)
def add_member(
    payload: MemberAdd,
    membership: Membership = Depends(require_permission("users:create")),
    orgs: OrgService = OrgSvc,
) -> Membership:
    return orgs.add_member(org_id=membership.org_id, actor=membership, payload=payload)


@router.patch("/current/members/{membership_id}", response_model=MemberRead)
def update_member_role(
    membership_id: int,
    payload: MemberUpdate,
    membership: Membership = Depends(require_permission("users:update")),
    orgs: OrgService = OrgSvc,
) -> Membership:
    return orgs.update_member_role(
        org_id=membership.org_id, actor=membership, membership_id=membership_id, payload=payload
    )


@router.delete("/current/members/{membership_id}", status_code=status.HTTP_204_NO_CONTENT)
def remove_member(
    membership_id: int,
    membership: Membership = Depends(require_permission("users:delete")),
    orgs: OrgService = OrgSvc,
) -> None:
    orgs.remove_member(org_id=membership.org_id, membership_id=membership_id)
