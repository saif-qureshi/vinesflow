def test_get_my_profile(client, register, h):
    token = register()
    res = client.get("/api/v1/users/me", headers=h(token))
    assert res.status_code == 200
    assert res.json()["data"]["email"] == "owner@test.io"


def test_update_profile_name_and_avatar(client, register, org_id_of, h):
    token = register()
    key = f"org-{org_id_of(token)}/x.png"
    res = client.patch(
        "/api/v1/users/me",
        headers=h(token),
        json={"full_name": "Renamed", "avatar_key": key},
    )
    assert res.status_code == 200
    data = res.json()["data"]
    assert data["full_name"] == "Renamed"
    assert data["avatar_key"] == key
    assert data["avatar_url"].endswith(key)


def test_update_password_then_relogin(client, register, h):
    token = register()
    assert client.patch("/api/v1/users/me", headers=h(token), json={"password": "newpass123"}).status_code == 200
    assert client.post(
        "/api/v1/auth/login", json={"email": "owner@test.io", "password": "password123"}
    ).status_code == 401
    assert client.post(
        "/api/v1/auth/login", json={"email": "owner@test.io", "password": "newpass123"}
    ).status_code == 200


def test_short_password_rejected(client, register, h):
    token = register()
    res = client.patch("/api/v1/users/me", headers=h(token), json={"password": "short"})
    assert res.status_code == 422
    assert res.json()["error"]["code"] == "validation_error"
