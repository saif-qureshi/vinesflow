from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from app.core.config import settings
from app.core.security import create_access_token, hash_password
from app.modules.orgs.models import Membership, Organization
from app.modules.users.models import User
from app.super_admin.auth.models import SuperAdmin


def _create_admin(db: Session, email: str = "admin@vineflow.example.com") -> SuperAdmin:
    admin = SuperAdmin(
        email=email,
        full_name="Super Admin",
        hashed_password=hash_password("admin-password"),
    )
    db.add(admin)
    db.commit()
    return admin


def _admin_login(client: TestClient) -> str:
    response = client.post(
        "/api/v1/super-admin/auth/login",
        json={"email": "admin@vineflow.example.com", "password": "admin-password"},
    )
    assert response.status_code == 200, response.text
    assert settings.SUPER_ADMIN_REFRESH_COOKIE_NAME in response.cookies
    return response.json()["data"]["access_token"]


def _onboard(client: TestClient, token: str) -> dict:
    response = client.post(
        "/api/v1/super-admin/organizations",
        headers={"Authorization": f"Bearer {token}"},
        json={
            "name": "Acme Distribution",
            "owner_email": "owner@acme.example.com",
            "owner_password": "owner-password",
            "owner_full_name": "Acme Owner",
            "currency": "pkr",
            "country": "pk",
            "industry": "Distribution",
            "fiscal_year_start_month": 7,
        },
    )
    assert response.status_code == 201, response.text
    return response.json()["data"]


def test_customer_superuser_is_not_a_super_admin(client: TestClient, db: Session):
    customer = User(
        email="staff@vineflow.example.com",
        hashed_password=hash_password("customer-password"),
        is_superuser=True,
    )
    db.add(customer)
    db.commit()

    login = client.post(
        "/api/v1/super-admin/auth/login",
        json={"email": customer.email, "password": "customer-password"},
    )
    assert login.status_code == 401

    customer_token = create_access_token(customer.id)
    dashboard = client.get(
        "/api/v1/super-admin/dashboard",
        headers={"Authorization": f"Bearer {customer_token}"},
    )
    assert dashboard.status_code == 401
    assert dashboard.json()["error"]["message"] == "Invalid token type"


def test_super_admin_auth_and_dashboard(client: TestClient, db: Session):
    _create_admin(db)
    token = _admin_login(client)

    me = client.get(
        "/api/v1/super-admin/auth/me",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert me.status_code == 200
    assert me.json()["data"]["email"] == "admin@vineflow.example.com"

    dashboard = client.get(
        "/api/v1/super-admin/dashboard",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert dashboard.status_code == 200
    assert dashboard.json()["data"] == {
        "organizations": 0,
        "active_organizations": 0,
        "inactive_organizations": 0,
        "organization_users": 0,
    }


def test_admin_onboarding_uses_customer_org_setup(client: TestClient, db: Session):
    _create_admin(db)
    token = _admin_login(client)
    organization = _onboard(client, token)

    owner = db.query(User).filter(User.email == "owner@acme.example.com").one()
    membership = (
        db.query(Membership)
        .filter(Membership.user_id == owner.id, Membership.org_id == organization["id"])
        .one()
    )
    assert membership.is_owner is True
    assert membership.role.org_id == organization["id"]
    assert organization["currency"] == "PKR"
    assert organization["country"] == "PK"
    assert organization["is_active"] is True

    listed = client.get(
        "/api/v1/super-admin/organizations",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert listed.status_code == 200
    assert listed.json()["data"]["total"] == 1
    assert listed.json()["data"]["items"][0]["owner_email"] == "owner@acme.example.com"

    detail = client.get(
        f"/api/v1/super-admin/organizations/{organization['id']}",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert detail.status_code == 200
    assert detail.json()["data"]["fiscal_year_start_month"] == 7

    updated = client.put(
        f"/api/v1/super-admin/organizations/{organization['id']}",
        headers={"Authorization": f"Bearer {token}"},
        json={
            "name": "Acme Distribution Pakistan",
            "currency": "usd",
            "country": "us",
            "industry": "Wholesale",
            "fiscal_year_start_month": 1,
            "is_active": True,
        },
    )
    assert updated.status_code == 200
    assert updated.json()["data"]["name"] == "Acme Distribution Pakistan"
    assert updated.json()["data"]["currency"] == "USD"
    assert updated.json()["data"]["country"] == "US"


def test_public_and_customer_org_registration_can_be_disabled(
    client: TestClient, db: Session, monkeypatch
):
    monkeypatch.setattr(settings, "PUBLIC_REGISTRATION_ENABLED", False)
    registration = client.post(
        "/api/v1/auth/register",
        json={
            "email": "public@test.io",
            "password": "password123",
            "full_name": "Public User",
            "org_name": "Public Org",
        },
    )
    assert registration.status_code == 403

    customer = User(
        email="customer@test.io",
        hashed_password=hash_password("password123"),
    )
    db.add(customer)
    db.commit()
    monkeypatch.setattr(settings, "SELF_SERVICE_ORG_CREATION_ENABLED", False)
    response = client.post(
        "/api/v1/orgs",
        headers={"Authorization": f"Bearer {create_access_token(customer.id)}"},
        json={"name": "Another Org"},
    )
    assert response.status_code == 403


def test_disabled_organization_is_blocked_from_customer_app(client: TestClient, db: Session):
    _create_admin(db)
    admin_token = _admin_login(client)
    organization = _onboard(client, admin_token)

    login = client.post(
        "/api/v1/auth/login",
        json={"email": "owner@acme.example.com", "password": "owner-password"},
    )
    customer_token = login.json()["data"]["access_token"]

    disabled = client.patch(
        f"/api/v1/super-admin/organizations/{organization['id']}/status",
        headers={"Authorization": f"Bearer {admin_token}"},
        json={"is_active": False},
    )
    assert disabled.status_code == 200
    assert disabled.json()["data"]["is_active"] is False
    assert db.get(Organization, organization["id"]).is_active is False

    me = client.get(
        "/api/v1/auth/me",
        headers={"Authorization": f"Bearer {customer_token}"},
    )
    assert me.status_code == 200
    assert me.json()["data"]["memberships"] == []

    current_org = client.get(
        "/api/v1/orgs/current",
        headers={
            "Authorization": f"Bearer {customer_token}",
            "X-Org-Id": str(organization["id"]),
        },
    )
    assert current_org.status_code == 403


def test_super_admin_refresh_token_rotates_and_reuse_is_rejected(client: TestClient, db: Session):
    _create_admin(db)
    _admin_login(client)
    old_refresh = client.cookies.get(settings.SUPER_ADMIN_REFRESH_COOKIE_NAME)

    rotated = client.post("/api/v1/super-admin/auth/refresh")
    assert rotated.status_code == 200
    assert client.cookies.get(settings.SUPER_ADMIN_REFRESH_COOKIE_NAME) != old_refresh

    client.cookies.set(
        settings.SUPER_ADMIN_REFRESH_COOKIE_NAME,
        old_refresh,
        path=settings.SUPER_ADMIN_REFRESH_COOKIE_PATH,
    )
    reused = client.post("/api/v1/super-admin/auth/refresh")
    assert reused.status_code == 401
    assert reused.json()["error"]["message"] == "Refresh token reuse detected"
