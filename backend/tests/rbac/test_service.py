import pytest

from app.core.exceptions import (
    BadRequestError,
    ConflictError,
    ForbiddenError,
    NotFoundError,
)
from app.core.security import hash_password
from app.modules.orgs.models import Membership
from app.modules.orgs.service import OrgService
from app.modules.rbac.constants import ALL_PERMISSION_CODES
from app.modules.rbac.schemas import RoleCreate, RoleUpdate
from app.modules.rbac.service import RbacService
from app.modules.users.models import User


def _org(db):
    owner = User(email="o@test.io", hashed_password=hash_password("password123"))
    db.add(owner)
    db.flush()
    org = OrgService(db).create_org_with_owner(owner=owner, name="Acme")
    db.flush()
    return org, owner


def _owner_membership(db, org, owner) -> Membership:
    return db.query(Membership).filter_by(org_id=org.id, user_id=owner.id).first()


def test_seed_permissions_is_idempotent(db):
    rbac = RbacService(db)
    first = rbac.seed_permissions()
    second = rbac.seed_permissions()
    assert set(first) == ALL_PERMISSION_CODES
    assert set(second) == ALL_PERMISSION_CODES


def test_create_role_resolves_permissions(db):
    org, owner = _org(db)
    role = RbacService(db).create_role(
        org_id=org.id,
        actor=_owner_membership(db, org, owner),
        payload=RoleCreate(name="Clerk", permissions=["invoices:read"]),
    )
    assert role.is_system is False
    assert [p.code for p in role.permissions] == ["invoices:read"]


def test_update_system_role_raises_bad_request(db):
    org, owner = _org(db)
    rbac = RbacService(db)
    admin_role = next(r for r in rbac.list_roles(org.id) if r.slug == "admin")
    with pytest.raises(BadRequestError):
        rbac.update_role(
            org_id=org.id,
            actor=_owner_membership(db, org, owner),
            role_id=admin_role.id,
            payload=RoleUpdate(name="X"),
        )


def test_get_role_in_wrong_org_raises_not_found(db):
    org, _ = _org(db)
    with pytest.raises(NotFoundError):
        RbacService(db).get_role_in_org(org.id, 999999)


def test_delete_role_in_use_raises_conflict(db):
    org, owner = _org(db)
    rbac = RbacService(db)
    role = rbac.create_role(
        org_id=org.id,
        actor=_owner_membership(db, org, owner),
        payload=RoleCreate(name="Clerk", permissions=[]),
    )
    # Assign the owner's membership to this role, then deletion must fail.
    membership = db.query(Membership).filter_by(org_id=org.id, user_id=owner.id).first()
    membership.role_id = role.id
    db.flush()
    with pytest.raises(ConflictError):
        rbac.delete_role(org_id=org.id, role_id=role.id)


def _limited_member(db, org, rbac, codes):
    user = User(email="lead@test.io", hashed_password=hash_password("password123"))
    db.add(user)
    db.flush()
    owner_membership = db.query(Membership).filter_by(org_id=org.id, is_owner=True).first()
    role = rbac.create_role(
        org_id=org.id, actor=owner_membership, payload=RoleCreate(name="Lead", permissions=codes)
    )
    membership = Membership(user_id=user.id, org_id=org.id, role_id=role.id, is_owner=False)
    db.add(membership)
    db.flush()
    return membership


def test_cannot_create_a_role_granting_permissions_the_actor_lacks(db):
    org, _ = _org(db)
    rbac = RbacService(db)
    actor = _limited_member(db, org, rbac, ["roles:create", "users:update"])

    with pytest.raises(ForbiddenError):
        rbac.create_role(
            org_id=org.id,
            actor=actor,
            payload=RoleCreate(name="Everything", permissions=sorted(ALL_PERMISSION_CODES)),
        )


def test_can_create_a_role_within_the_actors_own_permissions(db):
    org, _ = _org(db)
    rbac = RbacService(db)
    actor = _limited_member(db, org, rbac, ["roles:create", "users:update"])

    role = rbac.create_role(
        org_id=org.id, actor=actor, payload=RoleCreate(name="Helper", permissions=["users:update"])
    )
    assert [p.code for p in role.permissions] == ["users:update"]
