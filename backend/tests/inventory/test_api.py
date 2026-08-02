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


def test_bin_crud_and_opening_stock_breakdown(client, setup):
    hdr, pid, loc = setup["hdr"], setup["pid"], setup["loc_id"]
    created = client.post(
        "/api/v1/inventory/bins",
        headers=hdr,
        json={"location_id": loc, "code": " a-01 ", "name": "Rack A"},
    )
    assert created.status_code == 201, created.text
    bin_id = created.json()["data"]["id"]
    assert created.json()["data"]["code"] == "A-01"

    duplicate = client.post(
        "/api/v1/inventory/bins",
        headers=hdr,
        json={"location_id": loc, "code": "a-01", "name": "Duplicate"},
    )
    assert duplicate.status_code == 409

    listed = client.get(f"/api/v1/inventory/bins?location_id={loc}", headers=hdr)
    assert [row["id"] for row in listed.json()["data"]] == [bin_id]

    opening = client.post(
        "/api/v1/inventory/opening",
        headers=hdr,
        json={
            "product_id": pid,
            "entries": [
                {"location_id": loc, "bin_id": bin_id, "quantity": 8, "unit_cost": 5},
                {"location_id": loc, "quantity": 2, "unit_cost": 5},
            ],
        },
    )
    assert opening.status_code == 200, opening.text

    stock = client.get(f"/api/v1/inventory/{pid}/stock", headers=hdr).json()["data"]
    assert float(stock["on_hand"]) == 10
    quantities = {(row["bin_id"]): float(row["quantity"]) for row in stock["by_bin"]}
    assert quantities == {bin_id: 8, None: 2}

    deactivate = client.patch(
        f"/api/v1/inventory/bins/{bin_id}", headers=hdr, json={"is_active": False}
    )
    assert deactivate.status_code == 409
    assert client.delete(f"/api/v1/inventory/bins/{bin_id}", headers=hdr).status_code == 409
