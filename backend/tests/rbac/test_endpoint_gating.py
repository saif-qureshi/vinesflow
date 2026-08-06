import pytest


@pytest.fixture()
def restricted(client, register, org_id_of, h):
    """A member holding one narrow permission and nothing else."""
    owner = register()
    org = org_id_of(owner)
    token = register(email="narrow@test.io", org="Personal")
    role = client.post(
        "/api/v1/roles",
        headers=h(owner, org),
        json={"name": "Narrow", "permissions": ["parties:read"]},
    ).json()["data"]
    client.post(
        "/api/v1/orgs/current/members",
        headers=h(owner, org),
        json={"email": "narrow@test.io", "role_id": role["id"]},
    )
    return h(token, org)


@pytest.mark.parametrize(
    ("method", "path"),
    [
        ("get", "/api/v1/dashboard/summary"),
        ("get", "/api/v1/activities"),
        ("get", "/api/v1/permissions"),
        ("get", "/api/v1/tax-rates"),
        ("get", "/api/v1/sellable-items"),
        ("get", "/api/v1/stock-on-hand"),
        ("post", "/api/v1/fbr/invoices/1/validate"),
    ],
)
def test_membership_alone_does_not_grant_access(client, restricted, method, path):
    assert getattr(client, method)(path, headers=restricted).status_code == 403


def test_the_granted_permission_still_works(client, restricted):
    assert client.get("/api/v1/parties", headers=restricted).status_code == 200
