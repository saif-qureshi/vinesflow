import pytest


@pytest.fixture()
def setup(client, register, org_id_of, h):
    token = register()
    org = org_id_of(token)
    hdr = h(token, org)
    category_id = client.post("/api/v1/categories", headers=hdr, json={"name": "Electronics"}).json()["data"]["id"]
    uoms = client.get("/api/v1/uoms", headers=hdr).json()["data"]
    uom_id = next(u["id"] for u in uoms if u["symbol"] == "pc")
    return {"hdr": hdr, "org_id": org, "category_id": category_id, "uom_id": uom_id}


def test_create_product_with_refs_media_and_prices(client, setup):
    hdr, org_id = setup["hdr"], setup["org_id"]
    res = client.post(
        "/api/v1/products",
        headers=hdr,
        json={
            "name": "iPhone 16",
            "description": "Flagship phone",
            "nature": "good",
            "type": "single",
            "sku": "IP16",
            "category_id": setup["category_id"],
            "uom_id": setup["uom_id"],
            "sale_price": 999.99,
            "purchase_price": 750,
            "track_inventory": True,
            "reorder_point": 5,
            "media": [
                {"storage_key": f"org-{org_id}/img1.png"},
                {"storage_key": f"org-{org_id}/img2.png"},
            ],
        },
    )
    assert res.status_code == 201
    data = res.json()["data"]
    assert data["sku"] == "IP16"
    assert data["category"]["name"] == "Electronics"
    assert data["uom"]["symbol"] == "pc"
    assert data["sale_price"] == 999.99
    assert data["track_inventory"] is True
    assert [m["storage_key"] for m in data["media"]] == [
        f"org-{org_id}/img1.png",
        f"org-{org_id}/img2.png",
    ]
    assert all(m["url"].endswith(m["storage_key"]) for m in data["media"])


def test_duplicate_sku_conflicts(client, setup):
    hdr, uom_id = setup["hdr"], setup["uom_id"]
    client.post("/api/v1/products", headers=hdr, json={"name": "A", "sku": "DUP", "uom_id": uom_id})
    dup = client.post("/api/v1/products", headers=hdr, json={"name": "B", "sku": "DUP", "uom_id": uom_id})
    assert dup.status_code == 409


def test_unknown_category_returns_not_found(client, setup):
    res = client.post(
        "/api/v1/products", headers=setup["hdr"], json={"name": "X", "category_id": 99999}
    )
    assert res.status_code == 404


def test_goods_require_unit(client, setup):
    res = client.post("/api/v1/products", headers=setup["hdr"], json={"name": "NoUnit", "nature": "good"})
    assert res.status_code == 400


def test_update_replaces_media(client, setup):
    org_id = setup["org_id"]
    hdr = setup["hdr"]
    pid = client.post(
        "/api/v1/products",
        headers=hdr,
        json={
            "name": "Widget",
            "uom_id": setup["uom_id"],
            "media": [{"storage_key": f"org-{org_id}/old.png"}],
        },
    ).json()["data"]["id"]

    upd = client.patch(
        f"/api/v1/products/{pid}",
        headers=hdr,
        json={"sale_price": 42, "media": [{"storage_key": f"org-{org_id}/new.png"}]},
    )
    data = upd.json()["data"]
    assert data["sale_price"] == 42
    assert [m["storage_key"] for m in data["media"]] == [f"org-{org_id}/new.png"]


def test_product_media_rejects_a_key_outside_the_org(client, setup):
    res = client.post(
        "/api/v1/products",
        headers=setup["hdr"],
        json={
            "name": "Traversal",
            "uom_id": setup["uom_id"],
            "media": [{"storage_key": "/etc/passwd"}],
        },
    )
    assert res.status_code == 400


def test_list_and_delete(client, setup):
    hdr = setup["hdr"]
    pid = client.post(
        "/api/v1/products", headers=hdr, json={"name": "ToDelete", "uom_id": setup["uom_id"]}
    ).json()["data"]["id"]
    page = client.get("/api/v1/products", headers=hdr).json()["data"]
    assert any(p["id"] == pid for p in page["items"])
    assert client.delete(f"/api/v1/products/{pid}", headers=hdr).status_code == 204
    assert client.get(f"/api/v1/products/{pid}", headers=hdr).status_code == 404


def test_variable_product_with_variants(client, setup):
    hdr = setup["hdr"]
    res = client.post(
        "/api/v1/products",
        headers=hdr,
        json={
            "name": "T-Shirt",
            "type": "variable",
            "uom_id": setup["uom_id"],
            "variant_attributes": [
                {"name": "Color", "options": ["Red", "Blue"]},
                {"name": "Size", "options": ["S", "M"]},
            ],
            "variants": [
                {"options": {"Color": "Red", "Size": "S"}, "sku": "TS-R-S", "sale_price": 20},
                {"options": {"Color": "Blue", "Size": "M"}, "sku": "TS-B-M", "sale_price": 22},
            ],
        },
    )
    assert res.status_code == 201
    data = res.json()["data"]
    assert data["type"] == "variable"
    attrs = {a["name"]: set(a["options"]) for a in data["variant_attributes"]}
    assert attrs == {"Color": {"Red", "Blue"}, "Size": {"S", "M"}}
    assert len(data["variants"]) == 2
    first = data["variants"][0]
    assert first["sku"] == "TS-R-S"
    assert first["name"] == "T-Shirt / Red / S"
    assert {v["value"] for v in first["values"]} == {"Red", "S"}


def test_search_and_filter(client, setup):
    hdr = setup["hdr"]
    client.post(
        "/api/v1/products",
        headers=hdr,
        json={"name": "Blue Shirt", "nature": "good", "sku": "SH1", "uom_id": setup["uom_id"]},
    )
    client.post("/api/v1/products", headers=hdr, json={"name": "Consulting", "nature": "service"})

    by_search = client.get("/api/v1/products?search=shirt", headers=hdr).json()["data"]["items"]
    assert [p["name"] for p in by_search] == ["Blue Shirt"]

    by_sku = client.get("/api/v1/products?search=SH1", headers=hdr).json()["data"]["items"]
    assert [p["name"] for p in by_sku] == ["Blue Shirt"]

    services = client.get("/api/v1/products?nature=service", headers=hdr).json()["data"]["items"]
    assert [p["name"] for p in services] == ["Consulting"]

    in_category = client.get(
        f"/api/v1/products?category_id={setup['category_id']}", headers=hdr
    ).json()["data"]["items"]
    assert in_category == []


def test_cursor_pagination(client, setup):
    hdr = setup["hdr"]
    for i in range(5):
        client.post("/api/v1/products", headers=hdr, json={"name": f"P{i}", "uom_id": setup["uom_id"]})

    first = client.get("/api/v1/products?limit=2", headers=hdr).json()["data"]
    assert len(first["items"]) == 2
    assert first["has_more"] is True
    assert first["next_cursor"]

    second = client.get(
        f"/api/v1/products?limit=2&cursor={first['next_cursor']}", headers=hdr
    ).json()["data"]
    assert len(second["items"]) == 2
    # Pages must not overlap.
    assert {p["id"] for p in first["items"]}.isdisjoint({p["id"] for p in second["items"]})
