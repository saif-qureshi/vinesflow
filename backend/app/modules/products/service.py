from __future__ import annotations

from sqlalchemy import or_, select
from sqlalchemy.orm import Session

from app.core.exceptions import BadRequestError, ConflictError, NotFoundError
from app.core.pagination import paginate_cursor
from app.modules.activities.service import ActivityService
from app.modules.attributes.models import Attribute, AttributeValue
from app.modules.brands.models import Brand
from app.modules.categories.models import Category
from app.modules.manufacturers.models import Manufacturer
from app.modules.media.service import MediaService
from app.modules.products.models import PRODUCT_MEDIA_TYPE, Product
from app.modules.products.schemas import (
    ProductCreate,
    ProductListQuery,
    ProductUpdate,
    VariantAttributeInput,
    VariantInput,
)
from app.modules.uoms.models import Uom


class ProductService:
    def __init__(self, db: Session) -> None:
        self.db = db
        self.media = MediaService(db)
        self.activity = ActivityService(db)

    def list(self, org_id: int, query: ProductListQuery) -> tuple[list[Product], str | None, bool]:
        stmt = select(Product).where(Product.org_id == org_id, Product.parent_id.is_(None))
        if query.search:
            like = f"%{query.search.strip()}%"
            stmt = stmt.where(or_(Product.name.ilike(like), Product.sku.ilike(like)))
        if query.category_id is not None:
            stmt = stmt.where(Product.category_id == query.category_id)
        if query.brand_id is not None:
            stmt = stmt.where(Product.brand_id == query.brand_id)
        if query.manufacturer_id is not None:
            stmt = stmt.where(Product.manufacturer_id == query.manufacturer_id)
        if query.nature:
            stmt = stmt.where(Product.nature == query.nature)
        if query.type:
            stmt = stmt.where(Product.type == query.type)
        if query.is_active is not None:
            stmt = stmt.where(Product.is_active == query.is_active)
        return paginate_cursor(self.db, stmt, Product.id, query)

    def get(self, org_id: int, product_id: int) -> Product:
        product = self.db.scalar(
            select(Product).where(Product.id == product_id, Product.org_id == org_id)
        )
        if product is None:
            raise NotFoundError("Product not found")
        return product

    def item_sales(self, org_id: int, product_id: int, period: str) -> list[dict]:
        from decimal import Decimal

        from app.modules.documents.enums import DocumentStatus, DocumentType
        from app.modules.documents.models import Document, DocumentLine

        self.get(org_id, product_id)
        child_ids = list(
            self.db.scalars(
                select(Product.id).where(Product.org_id == org_id, Product.parent_id == product_id)
            )
        )
        ids = child_ids or [product_id]

        buckets = self._sales_buckets(period)
        rows = self.db.execute(
            select(Document.issue_date, DocumentLine.line_total)
            .join(DocumentLine, DocumentLine.document_id == Document.id)
            .where(
                Document.org_id == org_id,
                Document.type == DocumentType.INVOICE,
                Document.status == DocumentStatus.SENT,
                DocumentLine.product_id.in_(ids),
                Document.issue_date >= buckets[0][1],
                Document.issue_date <= buckets[-1][2],
            )
        ).all()

        out = [{"label": label, "sales": Decimal("0")} for label, _s, _e in buckets]
        for issue_date, line_total in rows:
            for i, (_label, start, end) in enumerate(buckets):
                if start <= issue_date <= end:
                    out[i]["sales"] += line_total or Decimal("0")
                    break
        return out

    @staticmethod
    def _sales_buckets(period: str) -> list[tuple]:
        from datetime import date, timedelta

        today = date.today()
        if period == "month":
            weeks = []
            for i in range(3, -1, -1):
                end = today - timedelta(days=7 * i)
                weeks.append((end.strftime("%d %b"), end - timedelta(days=6), end))
            return weeks
        months = 3 if period == "quarter" else 12
        out = []
        for i in range(months - 1, -1, -1):
            month = today.month - i
            year = today.year
            while month <= 0:
                month += 12
                year -= 1
            start = date(year, month, 1)
            end = (
                date(year, 12, 31) if month == 12 else date(year, month + 1, 1) - timedelta(days=1)
            )
            out.append((start.strftime("%b"), start, end))
        return out

    def _validate_refs(self, org_id: int, payload) -> None:
        refs = (
            (Category, payload.category_id, "Category"),
            (Uom, payload.uom_id, "Unit"),
            (Brand, payload.brand_id, "Brand"),
            (Manufacturer, payload.manufacturer_id, "Manufacturer"),
        )
        for model, ref_id, label in refs:
            if ref_id is None:
                continue
            if self.db.scalar(
                select(model.id).where(model.id == ref_id, model.org_id == org_id)
            ) is None:
                raise NotFoundError(f"{label} not found")

    def _require_uom_for_goods(self, nature: str, uom_id: int | None) -> None:
        if nature == "good" and uom_id is None:
            raise BadRequestError("A unit of measure is required for goods")

    def _ensure_unique_sku(
        self, org_id: int, sku: str | None, exclude_id: int | None = None
    ) -> None:
        if not sku:
            return
        q = select(Product.id).where(Product.org_id == org_id, Product.sku == sku)
        if exclude_id is not None:
            q = q.where(Product.id != exclude_id)
        if self.db.scalar(q) is not None:
            raise ConflictError("A product with that SKU already exists")

    def _upsert_values(
        self, org_id: int, attributes: list[VariantAttributeInput]
    ) -> dict[tuple[str, str], AttributeValue]:
        mapping: dict[tuple[str, str], AttributeValue] = {}
        for attr_input in attributes:
            attribute = self.db.scalar(
                select(Attribute).where(
                    Attribute.org_id == org_id, Attribute.name == attr_input.name
                )
            )
            if attribute is None:
                attribute = Attribute(org_id=org_id, name=attr_input.name)
                self.db.add(attribute)
                self.db.flush()
            existing = {v.value: v for v in attribute.values}
            for option in attr_input.options:
                value = existing.get(option)
                if value is None:
                    value = AttributeValue(org_id=org_id, attribute_id=attribute.id, value=option)
                    self.db.add(value)
                    self.db.flush()
                    existing[option] = value
                mapping[(attr_input.name, option)] = value
        return mapping

    def _apply_variants(
        self,
        org_id: int,
        product: Product,
        attributes: list[VariantAttributeInput],
        variants: list[VariantInput],
    ) -> None:
        mapping = self._upsert_values(org_id, attributes)
        product.attribute_values = list(mapping.values())

        existing = {v.id: v for v in product.variants}
        reconciled: list[Product] = []
        for i, v in enumerate(variants):
            values = [mapping[(a, val)] for a, val in v.options.items() if (a, val) in mapping]
            combo = " / ".join(v.options.values())
            name = v.name or f"{product.name} / {combo}" if combo else product.name
            child = existing.get(v.id) if v.id is not None else None
            if child is None:
                child = Product(org_id=org_id, parent_id=product.id, type="single")
            child.name = name
            child.nature = product.nature
            child.category_id = product.category_id
            child.brand_id = product.brand_id
            child.manufacturer_id = product.manufacturer_id
            child.uom_id = product.uom_id
            child.track_inventory = product.track_inventory
            child.tracking_mode = product.tracking_mode
            child.reorder_point = product.reorder_point
            child.sku = v.sku
            child.barcode = v.barcode
            child.sale_price = v.sale_price
            child.purchase_price = v.purchase_price
            child.is_active = v.is_active
            child.sort_order = i
            child.values = values
            reconciled.append(child)
        product.variants = reconciled

    def create(self, org_id: int, payload: ProductCreate) -> Product:
        self._validate_refs(org_id, payload)
        self._require_uom_for_goods(payload.nature, payload.uom_id)
        self._ensure_unique_sku(org_id, payload.sku)
        if payload.tracking_mode != "none" and not payload.track_inventory:
            raise BadRequestError("Lot or serial tracking requires inventory tracking")
        data = payload.model_dump(exclude={"media", "variant_attributes", "variants"})
        product = Product(org_id=org_id, **data)
        self.db.add(product)
        self.db.flush()
        self._apply_variants(org_id, product, payload.variant_attributes, payload.variants)
        self.media.replace_for(
            org_id=org_id,
            attachable_type=PRODUCT_MEDIA_TYPE,
            attachable_id=product.id,
            media=payload.media,
        )
        self.activity.record(org_id, "created", "product", product.name, entity_id=product.id)
        self.db.commit()
        self.db.refresh(product)
        return product

    def update(self, org_id: int, product_id: int, payload: ProductUpdate) -> Product:
        product = self.get(org_id, product_id)
        self._validate_refs(org_id, payload)
        if payload.sku is not None:
            self._ensure_unique_sku(org_id, payload.sku, exclude_id=product_id)

        fields = payload.model_fields_set
        nature = payload.nature if "nature" in fields else product.nature
        uom_id = payload.uom_id if "uom_id" in fields else product.uom_id
        self._require_uom_for_goods(nature, uom_id)
        track_inventory = (
            payload.track_inventory if "track_inventory" in fields else product.track_inventory
        )
        tracking_mode = (
            payload.tracking_mode if "tracking_mode" in fields else product.tracking_mode
        )
        if tracking_mode != "none" and not track_inventory:
            raise BadRequestError("Lot or serial tracking requires inventory tracking")
        if tracking_mode != product.tracking_mode:
            from app.modules.inventory.models import StockMovement

            tracked_product_ids = [product.id, *(variant.id for variant in product.variants)]
            if self.db.scalar(
                select(StockMovement.id)
                .where(
                    StockMovement.org_id == org_id,
                    StockMovement.product_id.in_(tracked_product_ids),
                )
                .limit(1)
            ):
                raise ConflictError(
                    "Tracking mode cannot be changed after inventory transactions exist"
                )

        scalar_fields = payload.model_dump(
            exclude_unset=True, exclude={"media", "variant_attributes", "variants"}
        )
        for key, value in scalar_fields.items():
            setattr(product, key, value)
        if product.type == "variable" and (
            "track_inventory" in fields or "tracking_mode" in fields
        ):
            for variant in product.variants:
                variant.track_inventory = product.track_inventory
                variant.tracking_mode = product.tracking_mode
        if payload.variant_attributes is not None:
            self._apply_variants(
                org_id, product, payload.variant_attributes, payload.variants or []
            )
        if payload.media is not None:
            self.media.replace_for(
                org_id=org_id,
                attachable_type=PRODUCT_MEDIA_TYPE,
                attachable_id=product_id,
                media=payload.media,
            )
        self.activity.record(org_id, "updated", "product", product.name, entity_id=product.id)
        self.db.commit()
        self.db.refresh(product)
        return product

    def delete(self, org_id: int, product_id: int) -> None:
        from app.modules.documents.models import DocumentLine
        from app.modules.inventory.models import StockMovement

        product = self.get(org_id, product_id)
        product_ids = [product.id, *(variant.id for variant in product.variants)]
        if self.db.scalar(
            select(StockMovement.id)
            .where(StockMovement.org_id == org_id, StockMovement.product_id.in_(product_ids))
            .limit(1)
        ):
            raise ConflictError("Item has stock history; deactivate it instead")
        if self.db.scalar(
            select(DocumentLine.id).where(DocumentLine.product_id.in_(product_ids)).limit(1)
        ):
            raise ConflictError("Item is used on documents; deactivate it instead")
        self.activity.record(org_id, "deleted", "product", product.name, entity_id=product_id)
        self.media.delete_for(org_id, PRODUCT_MEDIA_TYPE, product_id)
        self.db.delete(product)
        self.db.commit()
