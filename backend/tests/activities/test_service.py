from sqlalchemy import select

from app.core.security import hash_password
from app.modules.activities.models import Activity
from app.modules.activities.schemas import ActivityListQuery
from app.modules.activities.service import ActivityService
from app.modules.orgs.service import OrgService
from app.modules.products.schemas import ProductCreate
from app.modules.products.service import ProductService
from app.modules.uoms.models import Uom
from app.modules.users.models import User


def _org(db, email="a@test.io") -> tuple[int, int]:
    user = User(email=email, hashed_password=hash_password("password123"))
    db.add(user)
    db.flush()
    org = OrgService(db).create_org_with_owner(owner=user, name="Acme")
    db.flush()
    return org.id, user.id


def test_record_and_list(db):
    org_id, uid = _org(db)
    svc = ActivityService(db)
    svc.record(org_id, "created", "product", "Widget", entity_id=1, actor_id=uid)
    items, _, _ = svc.list(org_id, ActivityListQuery())
    assert len(items) == 1
    assert items[0].action == "created"
    assert items[0].summary == "Widget"
    assert items[0].actor_id == uid


def test_product_create_records_activity(db):
    org_id, _ = _org(db)
    uom_id = db.scalar(select(Uom.id).where(Uom.org_id == org_id).limit(1))
    product = ProductService(db).create(org_id, ProductCreate(name="Phone", uom_id=uom_id))
    acts = list(db.scalars(select(Activity).where(Activity.org_id == org_id)))
    assert any(
        a.action == "created" and a.entity_type == "product" and a.entity_id == product.id
        for a in acts
    )


def test_record_with_context_roundtrips(db):
    org_id, uid = _org(db)
    svc = ActivityService(db)
    svc.record(
        org_id,
        "submitted",
        "invoice",
        "INV-0001 · Acme Corp",
        entity_id=7,
        context={"amount": 1500, "party_id": 4, "status": "submitted"},
        actor_id=uid,
    )
    items, _, _ = svc.list(org_id, ActivityListQuery())
    assert items[0].action == "submitted"
    assert items[0].entity_type == "invoice"
    assert items[0].context == {"amount": 1500, "party_id": 4, "status": "submitted"}


def test_list_is_scoped_by_org(db):
    org_a, _ = _org(db)
    org_b, _ = _org(db, email="b@test.io")
    ActivityService(db).record(org_a, "created", "product", "A")
    items, _, _ = ActivityService(db).list(org_b, ActivityListQuery())
    assert items == []


def _org_events(db, org_id):
    return list(
        db.scalars(
            select(Activity).where(Activity.org_id == org_id, Activity.entity_type == "organization")
        )
    )


def test_org_update_recorded_branding_skipped(db):
    from app.modules.orgs.models import Membership
    from app.modules.orgs.schemas import OrgUpdate
    from app.modules.orgs.service import OrgService as Svc

    org_id, uid = _org(db)
    db.info["actor_id"] = uid
    membership = db.scalar(
        select(Membership).where(Membership.org_id == org_id, Membership.user_id == uid)
    )
    svc = Svc(db)

    svc.update_org(membership=membership, payload=OrgUpdate(name="Renamed"))
    assert len(_org_events(db, org_id)) == 1

    svc.update_org(membership=membership, payload=OrgUpdate(accent_color="#123456"))
    assert len(_org_events(db, org_id)) == 1


def test_role_create_recorded(db):
    from app.modules.rbac.schemas import RoleCreate
    from app.modules.rbac.service import RbacService

    from app.modules.orgs.models import Membership

    org_id, uid = _org(db)
    db.info["actor_id"] = uid
    actor = db.scalar(
        select(Membership).where(Membership.org_id == org_id, Membership.user_id == uid)
    )
    RbacService(db).create_role(
        org_id=org_id,
        actor=actor,
        payload=RoleCreate(name="Auditor", description="", permissions=["products:read"]),
    )
    acts = list(
        db.scalars(select(Activity).where(Activity.org_id == org_id, Activity.entity_type == "role"))
    )
    assert len(acts) == 1 and acts[0].action == "created"
