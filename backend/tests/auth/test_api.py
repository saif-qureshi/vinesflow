def test_register_creates_owner_membership(client, register, h):
    token = register()
    me = client.get("/api/v1/auth/me", headers=h(token)).json()["data"]
    assert me["user"]["email"] == "owner@test.io"
    assert len(me["memberships"]) == 1
    assert me["memberships"][0]["is_owner"] is True
    assert me["memberships"][0]["role"]["slug"] == "super_admin"


def test_login_wrong_password_returns_error_envelope(client, register):
    register()
    res = client.post("/api/v1/auth/login", json={"email": "owner@test.io", "password": "wrong"})
    assert res.status_code == 401
    body = res.json()
    assert body["success"] is False
    assert body["data"] is None
    assert body["error"]["code"] == "unauthorized"


def test_duplicate_email_conflict(client, register):
    register()
    res = client.post(
        "/api/v1/auth/register",
        json={"email": "owner@test.io", "password": "password123", "org_name": "Other"},
    )
    assert res.status_code == 409
    assert res.json()["error"]["code"] == "email_taken"


def test_refresh_rotates_and_detects_reuse(client, register):
    register()
    old = client.cookies.get("vf_refresh")
    assert old

    rotated = client.post("/api/v1/auth/refresh")
    assert rotated.status_code == 200
    assert client.cookies.get("vf_refresh") != old

    # Replaying the old (revoked) token trips reuse detection and kills the family.
    assert client.post("/api/v1/auth/refresh", cookies={"vf_refresh": old}).status_code == 401
    assert client.post("/api/v1/auth/refresh").status_code == 401


def test_logout_revokes_refresh(client, register):
    register()
    assert client.post("/api/v1/auth/logout").status_code == 200
    assert client.post("/api/v1/auth/refresh").status_code == 401


def test_me_requires_authentication(client):
    assert client.get("/api/v1/auth/me").status_code == 401


def test_changing_your_password_revokes_existing_sessions(client, register, h):
    token = register()
    refresh = client.cookies.get("vf_refresh")
    assert refresh

    assert (
        client.patch(
            "/api/v1/users/me", headers=h(token), json={"password": "newpass123"}
        ).status_code
        == 200
    )

    # The session that existed before the change must no longer mint tokens.
    assert client.post("/api/v1/auth/refresh", cookies={"vf_refresh": refresh}).status_code == 401
