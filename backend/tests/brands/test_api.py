import pytest


@pytest.fixture()
def hdr(client, register, org_id_of, h):
    token = register()
    return h(token, org_id_of(token))


@pytest.mark.parametrize("path", ["brands", "manufacturers"])
def test_crud_roundtrip(client, hdr, path):
    created = client.post(f"/api/v1/{path}", headers=hdr, json={"name": "Acme"})
    assert created.status_code == 201
    row = created.json()["data"]
    assert row["name"] == "Acme"
    assert row["is_active"] is True

    dup = client.post(f"/api/v1/{path}", headers=hdr, json={"name": "Acme"})
    assert dup.status_code == 409

    updated = client.patch(
        f"/api/v1/{path}/{row['id']}", headers=hdr, json={"name": "Acme Group", "is_active": False}
    )
    assert updated.status_code == 200
    assert updated.json()["data"]["name"] == "Acme Group"
    assert updated.json()["data"]["is_active"] is False

    assert [r["name"] for r in client.get(f"/api/v1/{path}", headers=hdr).json()["data"]] == [
        "Acme Group"
    ]
    assert client.delete(f"/api/v1/{path}/{row['id']}", headers=hdr).status_code == 204
    assert client.get(f"/api/v1/{path}", headers=hdr).json()["data"] == []


def test_product_carries_brand_and_manufacturer(client, hdr):
    brand = client.post("/api/v1/brands", headers=hdr, json={"name": "Dove"}).json()["data"]
    maker = client.post(
        "/api/v1/manufacturers", headers=hdr, json={"name": "Unilever"}
    ).json()["data"]
    uoms = client.get("/api/v1/uoms", headers=hdr).json()["data"]
    uom_id = next(u["id"] for u in uoms if u["symbol"] == "pc")

    created = client.post(
        "/api/v1/products",
        headers=hdr,
        json={
            "name": "Soap Bar",
            "uom_id": uom_id,
            "brand_id": brand["id"],
            "manufacturer_id": maker["id"],
        },
    )
    assert created.status_code == 201
    data = created.json()["data"]
    assert data["brand"]["name"] == "Dove"
    assert data["manufacturer"]["name"] == "Unilever"

    listed = client.get(f"/api/v1/products?brand_id={brand['id']}", headers=hdr).json()["data"]
    assert [p["name"] for p in listed["items"]] == ["Soap Bar"]


def test_a_brand_in_use_cannot_be_deleted(client, hdr):
    brand = client.post("/api/v1/brands", headers=hdr, json={"name": "Dove"}).json()["data"]
    uoms = client.get("/api/v1/uoms", headers=hdr).json()["data"]
    uom_id = next(u["id"] for u in uoms if u["symbol"] == "pc")
    client.post(
        "/api/v1/products",
        headers=hdr,
        json={"name": "Soap Bar", "uom_id": uom_id, "brand_id": brand["id"]},
    )
    assert client.delete(f"/api/v1/brands/{brand['id']}", headers=hdr).status_code == 409


def test_unknown_brand_is_rejected(client, hdr):
    uoms = client.get("/api/v1/uoms", headers=hdr).json()["data"]
    uom_id = next(u["id"] for u in uoms if u["symbol"] == "pc")
    res = client.post(
        "/api/v1/products",
        headers=hdr,
        json={"name": "Ghost", "uom_id": uom_id, "brand_id": 999999},
    )
    assert res.status_code == 404
