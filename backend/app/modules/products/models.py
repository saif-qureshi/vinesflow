from __future__ import annotations

from decimal import Decimal

from sqlalchemy import (
    Boolean,
    Column,
    ForeignKey,
    Integer,
    Numeric,
    String,
    Table,
    Text,
    UniqueConstraint,
    and_,
)
from sqlalchemy.orm import Mapped, foreign, mapped_column, relationship

from app.db.base_class import AuditMixin, Base, TimestampMixin
from app.modules.attributes.models import AttributeValue
from app.modules.categories.models import Category
from app.modules.media.models import MediaAsset
from app.modules.uoms.models import Uom

PRODUCT_MEDIA_TYPE = "product"

# The attribute values a variable product is offered in.
product_attribute_values = Table(
    "product_attribute_values",
    Base.metadata,
    Column("product_id", ForeignKey("products.id", ondelete="CASCADE"), primary_key=True),
    Column("attribute_value_id", ForeignKey("attribute_values.id", ondelete="CASCADE"), primary_key=True),
)

# The specific value per attribute a variant (a child product) represents.
variant_values = Table(
    "variant_values",
    Base.metadata,
    Column("product_id", ForeignKey("products.id", ondelete="CASCADE"), primary_key=True),
    Column("attribute_value_id", ForeignKey("attribute_values.id", ondelete="CASCADE"), primary_key=True),
)


class Product(Base, TimestampMixin, AuditMixin):
    __tablename__ = "products"
    __table_args__ = (UniqueConstraint("org_id", "sku", name="uq_product_org_sku"),)

    id: Mapped[int] = mapped_column(primary_key=True)
    org_id: Mapped[int] = mapped_column(
        ForeignKey("organizations.id", ondelete="CASCADE"), index=True, nullable=False
    )
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    nature: Mapped[str] = mapped_column(String(20), default="good", server_default="good", nullable=False)
    type: Mapped[str] = mapped_column(String(20), default="single", server_default="single", nullable=False)
    sku: Mapped[str | None] = mapped_column(String(100), nullable=True)
    barcode: Mapped[str | None] = mapped_column(String(64), nullable=True)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)

    sale_price: Mapped[Decimal | None] = mapped_column(Numeric(14, 2), nullable=True)
    purchase_price: Mapped[Decimal | None] = mapped_column(Numeric(14, 2), nullable=True)

    hs_code: Mapped[str | None] = mapped_column(String(20), nullable=True)
    uom_code: Mapped[str | None] = mapped_column(String(20), nullable=True)
    sale_type_code: Mapped[str | None] = mapped_column(String(20), nullable=True)
    tax_rate_code: Mapped[str | None] = mapped_column(String(20), nullable=True)
    sro_schedule_code: Mapped[str | None] = mapped_column(String(20), nullable=True)
    sro_item_serial: Mapped[str | None] = mapped_column(String(30), nullable=True)

    track_inventory: Mapped[bool] = mapped_column(
        Boolean, default=False, server_default="false", nullable=False
    )
    reorder_point: Mapped[int | None] = mapped_column(Integer, nullable=True)

    category_id: Mapped[int | None] = mapped_column(
        ForeignKey("categories.id", ondelete="SET NULL"), nullable=True
    )
    uom_id: Mapped[int | None] = mapped_column(
        ForeignKey("uoms.id", ondelete="SET NULL"), nullable=True
    )
    # A variant is a child product of its "variable" group parent.
    parent_id: Mapped[int | None] = mapped_column(
        ForeignKey("products.id", ondelete="CASCADE"), index=True, nullable=True
    )
    sort_order: Mapped[int] = mapped_column(Integer, default=0, server_default="0", nullable=False)

    category: Mapped[Category | None] = relationship(lazy="selectin")
    uom: Mapped[Uom | None] = relationship(lazy="selectin")
    # For a group product: the attribute values it is offered in.
    attribute_values: Mapped[list[AttributeValue]] = relationship(
        secondary=product_attribute_values, lazy="selectin"
    )
    # Child variant products of a group.
    variants: Mapped[list[Product]] = relationship(
        "Product",
        back_populates="parent",
        cascade="all, delete-orphan",
        order_by="Product.sort_order",
        lazy="selectin",
    )
    parent: Mapped[Product | None] = relationship(
        "Product", back_populates="variants", remote_side=[id]
    )
    # For a variant: the specific attribute values it represents.
    values: Mapped[list[AttributeValue]] = relationship(secondary=variant_values, lazy="selectin")
    media: Mapped[list[MediaAsset]] = relationship(
        primaryjoin=lambda: and_(
            foreign(MediaAsset.attachable_id) == Product.id,
            MediaAsset.attachable_type == PRODUCT_MEDIA_TYPE,
        ),
        order_by=lambda: MediaAsset.sort_order,
        viewonly=True,
        lazy="selectin",
    )

    def fbr(self, name: str) -> str | None:
        value = getattr(self, name)
        return value if value or self.parent is None else getattr(self.parent, name)

    @property
    def variant_attributes(self) -> list[dict]:
        """Group the product's linked values back into {name, options} form."""
        groups: dict[str, list[str]] = {}
        for value in self.attribute_values:
            groups.setdefault(value.attribute.name, []).append(value.value)
        return [{"name": name, "options": options} for name, options in groups.items()]
