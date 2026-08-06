from __future__ import annotations

from datetime import timedelta
from decimal import Decimal

from sqlalchemy import and_, func, select

from app.modules.brands.models import Brand
from app.modules.inventory.models import StockLevel, StockMovement
from app.modules.manufacturers.models import Manufacturer
from app.modules.products.models import Product
from app.modules.reports.contract import Column, Filter, ReportDef, ReportResult, Section
from app.modules.reports.registry import register

_ZERO = Decimal("0")


def _period(params: dict) -> str:
    return f"From {params['start'].isoformat()} to {params['end'].isoformat()}"


def _product_names(db, org_id) -> dict[int, str]:
    return dict(db.execute(select(Product.id, Product.name).where(Product.org_id == org_id)).all())


def _movement_value(qty_delta, unit_cost, value_delta) -> Decimal | None:
    if value_delta is not None:
        return value_delta
    if unit_cost is not None:
        return unit_cost * qty_delta
    return None


# --- Inventory Summary ---------------------------------------------------


def _int_or_none(value) -> int | None:
    return int(value) if value not in (None, "") else None


_SUMMARY_COLUMNS = [
    Column("item", "Item"),
    Column("sku", "SKU"),
    Column("brand", "Brand"),
    Column("manufacturer", "Manufacturer"),
    Column("quantity", "Stock on Hand", "number", "right"),
    Column("value", "Asset Value", "money", "right"),
]


def _inventory_summary(db, org_id, params):
    location_id = _int_or_none(params.get("location_id"))
    brand_id = _int_or_none(params.get("brand_id"))
    manufacturer_id = _int_or_none(params.get("manufacturer_id"))

    levels = StockLevel.product_id == Product.id
    if location_id is not None:
        levels = and_(levels, StockLevel.location_id == location_id)

    stmt = (
        select(
            Product.name,
            Product.sku,
            Brand.name,
            Manufacturer.name,
            Product.purchase_price,
            func.coalesce(func.sum(StockLevel.quantity), 0),
        )
        .join(StockLevel, levels, isouter=True)
        .join(Brand, Brand.id == Product.brand_id, isouter=True)
        .join(Manufacturer, Manufacturer.id == Product.manufacturer_id, isouter=True)
        .where(
            Product.org_id == org_id,
            Product.track_inventory.is_(True),
            Product.type != "variable",
        )
        .group_by(Product.id, Brand.name, Manufacturer.name)
        .order_by(Product.name)
    )
    if brand_id is not None:
        stmt = stmt.where(Product.brand_id == brand_id)
    if manufacturer_id is not None:
        stmt = stmt.where(Product.manufacturer_id == manufacturer_id)

    section_rows = []
    total_value = total_qty = _ZERO
    for name, sku, brand, maker, cost, qty in db.execute(stmt).all():
        qty = qty or _ZERO
        value = qty * (cost or _ZERO)
        total_value += value
        total_qty += qty
        section_rows.append(
            {
                "item": name,
                "sku": sku or "",
                "brand": brand or "",
                "manufacturer": maker or "",
                "quantity": qty,
                "value": value,
            }
        )
    return ReportResult(
        title="Inventory Summary",
        columns=_SUMMARY_COLUMNS,
        sections=[Section(rows=section_rows)],
        grand_total={"item": "Total", "quantity": total_qty, "value": total_value},
    )


# --- Stock Movement / Adjustments ---------------------------------------


def _movements(db, org_id, params, *, types=None, title, with_type_column):
    names = _product_names(db, org_id)
    stmt = (
        select(StockMovement)
        .where(
            StockMovement.org_id == org_id,
            StockMovement.created_at >= params["start"],
            StockMovement.created_at < params["end"] + timedelta(days=1),
        )
        .order_by(StockMovement.created_at, StockMovement.id)
    )
    if types is not None:
        stmt = stmt.where(StockMovement.type.in_(types))
    movements = db.scalars(stmt)

    section_rows = []
    total_value = _ZERO
    for m in movements:
        value = _movement_value(m.qty_delta, m.unit_cost, m.value_delta)
        if value is not None:
            total_value += value
        row = {
            "date": m.created_at.date(),
            "item": names.get(m.product_id, f"#{m.product_id}"),
            "reason": m.reason or (m.reference_type or ""),
            "quantity": m.qty_delta,
            "value": value,
        }
        if with_type_column:
            row["type"] = m.type
        section_rows.append(row)

    columns = [Column("date", "Date", "date"), Column("item", "Item")]
    if with_type_column:
        columns.append(Column("type", "Type"))
    columns += [
        Column("reason", "Reason / Source"),
        Column("quantity", "Qty", "number", "right"),
        Column("value", "Value", "money", "right"),
    ]
    return ReportResult(
        title=title,
        subtitle=_period(params),
        columns=columns,
        sections=[Section(rows=section_rows)],
        grand_total={"item": "Total", "value": total_value},
    )


def _stock_movement(db, org_id, params):
    return _movements(db, org_id, params, title="Stock Movement", with_type_column=True)


def _adjustments(db, org_id, params):
    return _movements(
        db,
        org_id,
        params,
        types=["adjustment", "revaluation"],
        title="Inventory Adjustment Details",
        with_type_column=False,
    )


register(
    ReportDef(
        key="inventory_summary",
        name="Inventory Summary",
        category="Inventory",
        description="Current stock on hand and asset value per item.",
        columns=_SUMMARY_COLUMNS,
        filters=[
            Filter("location_id", "select", "Branch", source="locations"),
            Filter("brand_id", "select", "Brand", source="brands"),
            Filter("manufacturer_id", "select", "Manufacturer", source="manufacturers"),
        ],
        run=_inventory_summary,
    )
)
register(
    ReportDef(
        key="stock_movement",
        name="Stock Movement",
        category="Inventory",
        description="Every stock in/out movement over a period.",
        columns=[
            Column("date", "Date", "date"),
            Column("item", "Item"),
            Column("type", "Type"),
            Column("reason", "Reason / Source"),
            Column("quantity", "Qty", "number", "right"),
            Column("value", "Value", "money", "right"),
        ],
        filters=[Filter("range", "date_range", "Date range", default="this_month")],
        run=_stock_movement,
    )
)
register(
    ReportDef(
        key="inventory_adjustment_details",
        name="Inventory Adjustment Details",
        category="Inventory",
        description="Stock adjustments and revaluations over a period.",
        columns=[
            Column("date", "Date", "date"),
            Column("item", "Item"),
            Column("reason", "Reason / Source"),
            Column("quantity", "Qty", "number", "right"),
            Column("value", "Value", "money", "right"),
        ],
        filters=[Filter("range", "date_range", "Date range", default="this_month")],
        run=_adjustments,
    )
)
