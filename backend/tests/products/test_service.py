import pytest
from sqlalchemy import select

from app.core.exceptions import BadRequestError, ConflictError, NotFoundError
from app.core.security import hash_password
from app.modules.categories.schemas import CategoryCreate
from app.modules.categories.service import CategoryService
from app.modules.media.models import MediaAsset
from app.modules.media.service import MediaService
from app.modules.orgs.service import OrgService
from app.modules.products.models import PRODUCT_MEDIA_TYPE
from app.modules.products.schemas import ProductCreate
from app.modules.products.service import ProductService
from app.modules.uoms.models import Uom
from app.modules.users.models import User


def _org(db) -> int:
    user = User(email="o@test.io", hashed_password=hash_password("password123"))
    db.add(user)
    db.flush()
    org = OrgService(db).create_org_with_owner(owner=user, name="Acme")
    db.flush()
    return org.id


def _uom(db, org_id: int) -> int:
    return db.scalar(select(Uom.id).where(Uom.org_id == org_id).limit(1))


def test_create_product_persists_media(db):
    org_id = _org(db)
    product = ProductService(db).create(
        org_id,
        ProductCreate(
            name="Item",
            uom_id=_uom(db, org_id),
            media=[
                {"storage_key": f"org-{org_id}/a.png"},
                {"storage_key": f"org-{org_id}/b.png"},
            ],
        ),
    )
    media = MediaService(db).list_for(org_id, PRODUCT_MEDIA_TYPE, product.id)
    assert [m.storage_key for m in media] == [f"org-{org_id}/a.png", f"org-{org_id}/b.png"]


def test_goods_require_uom(db):
    org_id = _org(db)
    with pytest.raises(BadRequestError):
        ProductService(db).create(org_id, ProductCreate(name="Item", nature="good"))


def test_fbr_fields_round_trip(db):
    org_id = _org(db)
    svc = ProductService(db)
    product = svc.create(
        org_id,
        ProductCreate(
            name="Phone",
            uom_id=_uom(db, org_id),
            hs_code="8517.1300",
            uom_code="100",
            sale_type_code="75",
            tax_rate_code="728",
        ),
    )
    assert product.hs_code == "8517.1300"
    assert product.sale_type_code == "75"

    from app.modules.products.schemas import ProductUpdate

    updated = svc.update(org_id, product.id, ProductUpdate(tax_rate_code="280"))
    assert updated.tax_rate_code == "280"
    assert updated.hs_code == "8517.1300"


def test_audit_fields_from_session_actor(db):
    from app.modules.products.schemas import ProductUpdate

    user = User(email="auditor@test.io", hashed_password=hash_password("password123"))
    db.add(user)
    db.flush()
    org = OrgService(db).create_org_with_owner(owner=user, name="Acme")
    db.flush()
    db.info["actor_id"] = user.id

    svc = ProductService(db)
    product = svc.create(org.id, ProductCreate(name="Phone", uom_id=_uom(db, org.id)))
    assert product.created_by_id == user.id
    assert product.updated_by_id == user.id

    other = User(email="editor@test.io", hashed_password=hash_password("password123"))
    db.add(other)
    db.flush()
    db.info["actor_id"] = other.id
    svc.update(org.id, product.id, ProductUpdate(sale_price=5))
    assert product.created_by_id == user.id
    assert product.updated_by_id == other.id


def test_service_does_not_require_uom(db):
    org_id = _org(db)
    product = ProductService(db).create(org_id, ProductCreate(name="Consulting", nature="service"))
    assert product.uom_id is None


def test_sku_uniqueness_enforced(db):
    org_id = _org(db)
    svc = ProductService(db)
    uom_id = _uom(db, org_id)
    svc.create(org_id, ProductCreate(name="A", sku="X1", uom_id=uom_id))
    with pytest.raises(ConflictError):
        svc.create(org_id, ProductCreate(name="B", sku="X1", uom_id=uom_id))


def test_invalid_category_ref_raises_not_found(db):
    org_id = _org(db)
    with pytest.raises(NotFoundError):
        ProductService(db).create(org_id, ProductCreate(name="A", category_id=4242))


def test_delete_removes_media(db):
    org_id = _org(db)
    svc = ProductService(db)
    product = svc.create(
        org_id,
        ProductCreate(
            name="A",
            uom_id=_uom(db, org_id),
            media=[{"storage_key": f"org-{org_id}/a.png"}],
        ),
    )
    pid = product.id
    svc.delete(org_id, pid)
    assert db.query(MediaAsset).filter_by(attachable_type=PRODUCT_MEDIA_TYPE, attachable_id=pid).count() == 0


def test_variant_attributes_are_reused_org_wide(db):
    from app.modules.attributes.models import Attribute
    from app.modules.products.schemas import VariantAttributeInput, VariantInput

    org_id = _org(db)
    svc = ProductService(db)
    uom_id = _uom(db, org_id)
    svc.create(
        org_id,
        ProductCreate(
            name="A",
            type="variable",
            uom_id=uom_id,
            variant_attributes=[VariantAttributeInput(name="Color", options=["Red"])],
            variants=[VariantInput(options={"Color": "Red"})],
        ),
    )
    svc.create(
        org_id,
        ProductCreate(
            name="B",
            type="variable",
            uom_id=uom_id,
            variant_attributes=[VariantAttributeInput(name="Color", options=["Red", "Green"])],
            variants=[VariantInput(options={"Color": "Green"})],
        ),
    )
    colors = db.query(Attribute).filter_by(org_id=org_id, name="Color").all()
    assert len(colors) == 1


def test_valid_category_link(db):
    org_id = _org(db)
    category = CategoryService(db).create(org_id, CategoryCreate(name="Cat"))
    product = ProductService(db).create(
        org_id, ProductCreate(name="A", category_id=category.id, uom_id=_uom(db, org_id))
    )
    assert product.category.name == "Cat"


def test_update_preserves_variant_ids(db):
    from app.modules.products.schemas import (
        ProductUpdate,
        VariantAttributeInput,
        VariantInput,
    )

    org_id = _org(db)
    svc = ProductService(db)
    product = svc.create(
        org_id,
        ProductCreate(
            name="Shirt",
            type="variable",
            uom_id=_uom(db, org_id),
            variant_attributes=[VariantAttributeInput(name="Color", options=["Red", "Blue"])],
            variants=[
                VariantInput(options={"Color": "Red"}, sale_price=100),
                VariantInput(options={"Color": "Blue"}, sale_price=100),
            ],
        ),
    )
    by_color = {v.values[0].value: v for v in product.variants}
    red_id, blue_id = by_color["Red"].id, by_color["Blue"].id

    updated = svc.update(
        org_id,
        product.id,
        ProductUpdate(
            variant_attributes=[VariantAttributeInput(name="Color", options=["Red", "Blue"])],
            variants=[
                VariantInput(id=red_id, options={"Color": "Red"}, sale_price=250),
                VariantInput(id=blue_id, options={"Color": "Blue"}, sale_price=100),
            ],
        ),
    )
    after = {v.values[0].value: v for v in updated.variants}
    assert after["Red"].id == red_id
    assert after["Blue"].id == blue_id
    assert after["Red"].sale_price == 250


def test_update_adds_and_removes_variants(db):
    from app.modules.products.models import Product
    from app.modules.products.schemas import (
        ProductUpdate,
        VariantAttributeInput,
        VariantInput,
    )

    org_id = _org(db)
    svc = ProductService(db)
    product = svc.create(
        org_id,
        ProductCreate(
            name="Shirt",
            type="variable",
            uom_id=_uom(db, org_id),
            variant_attributes=[VariantAttributeInput(name="Color", options=["Red", "Blue"])],
            variants=[
                VariantInput(options={"Color": "Red"}),
                VariantInput(options={"Color": "Blue"}),
            ],
        ),
    )
    red_id = next(v.id for v in product.variants if v.values[0].value == "Red")

    svc.update(
        org_id,
        product.id,
        ProductUpdate(
            variant_attributes=[VariantAttributeInput(name="Color", options=["Red", "Green"])],
            variants=[
                VariantInput(id=red_id, options={"Color": "Red"}),
                VariantInput(options={"Color": "Green"}),
            ],
        ),
    )
    values = {v.values[0].value: v.id for v in product.variants}
    assert set(values) == {"Red", "Green"}
    assert values["Red"] == red_id
    assert db.query(Product).filter_by(parent_id=product.id).count() == 2
