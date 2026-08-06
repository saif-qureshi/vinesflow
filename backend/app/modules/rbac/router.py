from __future__ import annotations

from fastapi import APIRouter, Depends, status

from app.api.deps import require_permission
from app.core.container import Provide
from app.core.responses import EnvelopeRoute
from app.modules.orgs.models import Membership
from app.modules.rbac.models import Permission, Role
from app.modules.rbac.schemas import PermissionRead, RoleCreate, RoleRead, RoleUpdate
from app.modules.rbac.service import RbacService

router = APIRouter(tags=["rbac"], route_class=EnvelopeRoute)

RbacSvc = Depends(Provide(RbacService))


@router.get("/permissions", response_model=list[PermissionRead])
def list_permissions(
    membership: Membership = Depends(require_permission("roles:read")),
    rbac: RbacService = RbacSvc,
) -> list[Permission]:
    return rbac.list_permissions()


@router.get("/roles", response_model=list[RoleRead])
def list_roles(
    membership: Membership = Depends(require_permission("roles:read")),
    rbac: RbacService = RbacSvc,
) -> list[Role]:
    return rbac.list_roles(membership.org_id)


@router.post("/roles", response_model=RoleRead, status_code=status.HTTP_201_CREATED)
def create_role(
    payload: RoleCreate,
    membership: Membership = Depends(require_permission("roles:create")),
    rbac: RbacService = RbacSvc,
) -> Role:
    return rbac.create_role(org_id=membership.org_id, actor=membership, payload=payload)


@router.get("/roles/{role_id}", response_model=RoleRead)
def get_role(
    role_id: int,
    membership: Membership = Depends(require_permission("roles:read")),
    rbac: RbacService = RbacSvc,
) -> Role:
    return rbac.get_role_in_org(membership.org_id, role_id)


@router.patch("/roles/{role_id}", response_model=RoleRead)
def update_role(
    role_id: int,
    payload: RoleUpdate,
    membership: Membership = Depends(require_permission("roles:update")),
    rbac: RbacService = RbacSvc,
) -> Role:
    return rbac.update_role(
        org_id=membership.org_id, actor=membership, role_id=role_id, payload=payload
    )


@router.delete("/roles/{role_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_role(
    role_id: int,
    membership: Membership = Depends(require_permission("roles:delete")),
    rbac: RbacService = RbacSvc,
) -> None:
    rbac.delete_role(org_id=membership.org_id, role_id=role_id)
