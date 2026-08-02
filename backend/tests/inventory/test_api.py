import pytest


@pytest.fixture()
def setup(client, register, org_id_of, h):
    token = register()
    hdr = h(token, org_id_of(token))
    uoms = client.get("/api/v1/uoms", headers=hdr).json()["data"]
    uom_id = next(u["id"] for u in uoms if u["symbol"] == "pc")
    pid = client.post(
        "/api/v1/products",
        headers=hdr,
        json={"name": "Widget", "uom_id": uom_id, "track_inventory": True, "reorder_point": 5},
    ).json()["data"]["id"]
    loc_id = client.get("/api/v1/locations", headers=hdr).json()["data"][0]["id"]
    return {"hdr": hdr, "pid": pid, "loc_id": loc_id}


def test_default_location_exists(client, setup):
    locations = client.get("/api/v1/locations", headers=setup["hdr"]).json()["data"]
    assert any(loc["is_default"] and loc["name"] == "Main Warehouse" for loc in locations)


def test_adjust_reflects_in_stock_and_list(client, setup):
    hdr, pid, loc = setup["hdr"], setup["pid"], setup["loc_id"]
    res = client.post(
        "/api/v1/inventory/adjust",
        headers=hdr,
        json={"product_id": pid, "location_id": loc, "qty_delta": 12},
    )
    assert res.status_code == 204

    stock = client.get(f"/api/v1/inventory/{pid}/stock", headers=hdr).json()["data"]
    assert float(stock["on_hand"]) == 12

    items = client.get("/api/v1/inventory", headers=hdr).json()["data"]["items"]
    row = next(i for i in items if i["id"] == pid)
    assert float(row["on_hand"]) == 12 and row["is_low"] is False


def test_low_stock_filter(client, setup):
    hdr, pid, loc = setup["hdr"], setup["pid"], setup["loc_id"]
    client.post(
        "/api/v1/inventory/adjust",
        headers=hdr,
        json={"product_id": pid, "location_id": loc, "qty_delta": 2},
    )
    low = client.get("/api/v1/inventory?low_stock=true", headers=hdr).json()["data"]["items"]
    assert any(i["id"] == pid and i["is_low"] for i in low)


def test_opening_stock_can_be_set_until_an_inventory_transaction_exists(client, setup):
    hdr, pid, loc = setup["hdr"], setup["pid"], setup["loc_id"]
    opening = client.post(
        "/api/v1/inventory/opening",
        headers=hdr,
        json={
            "product_id": pid,
            "date": "2026-08-01",
            "entries": [{"location_id": loc, "quantity": 12, "unit_cost": 25}],
        },
    )
    assert opening.status_code == 200, opening.text
    data = opening.json()["data"]
    assert data["editable"] is True
    assert float(data["entries"][0]["quantity"]) == 12
    assert float(data["entries"][0]["value"]) == 300

    stock = client.get(f"/api/v1/inventory/{pid}/stock", headers=hdr).json()["data"]
    assert float(stock["opening_stock"]) == 12
    assert float(stock["on_hand"]) == 12

    adjusted = client.post(
        "/api/v1/inventory/adjust",
        headers=hdr,
        json={"product_id": pid, "location_id": loc, "qty_delta": 1},
    )
    assert adjusted.status_code == 204

    locked = client.post(
        "/api/v1/inventory/opening",
        headers=hdr,
        json={
            "product_id": pid,
            "entries": [{"location_id": loc, "quantity": 15, "unit_cost": 25}],
        },
    )
    assert locked.status_code == 409
    state = client.get(f"/api/v1/inventory/{pid}/opening", headers=hdr).json()["data"]
    assert state["editable"] is False
