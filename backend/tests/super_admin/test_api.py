from cryptography.fernet import Fernet
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from app.core.config import settings
from app.core.crypto import _cipher
from app.core.security import create_access_token, hash_password
from app.core.storage import StoredFile
from app.modules.auth.models import RefreshSession
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
    dashboard_data = dashboard.json()["data"]
    assert dashboard_data["organizations"] == 0
    assert dashboard_data["active_organizations"] == 0
    assert dashboard_data["inactive_organizations"] == 0
    assert dashboard_data["organization_users"] == 0
    assert dashboard_data["new_organizations_30d"] == 0
    assert dashboard_data["fbr_enabled_organizations"] == 0
    assert dashboard_data["tax_identity_organizations"] == 0
    assert dashboard_data["fbr_configuration_issues"] == 0
    assert dashboard_data["recent_organizations"] == []
    assert len(dashboard_data["activity_14d"]) == 14
    assert all(point["customer_logins"] == 0 for point in dashboard_data["activity_14d"])
    assert len(dashboard_data["fbr_invoice_activity_14d"]) == 14
    assert all(
        point["submitted"] == 0 and point["draft"] == 0 and point["failed"] == 0
        for point in dashboard_data["fbr_invoice_activity_14d"]
    )


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
    assert detail.json()["data"]["members"][0]["is_owner"] is True
    assert detail.json()["data"]["members"][0]["email"] == "owner@acme.example.com"

    updated = client.put(
        f"/api/v1/super-admin/organizations/{organization['id']}",
        headers={"Authorization": f"Bearer {token}"},
        json={
            "name": "Acme Distribution Pakistan",
            "currency": "usd",
            "country": "us",
            "industry": "Wholesale",
            "ntn": "1234567",
            "strn": "1234567890123",
            "cnic": "3520212345678",
            "logo_key": f"org-{organization['id']}/acme.png",
            "address": {
                "line1": "1 Commerce Street",
                "city": "Karachi",
                "state": "Sindh",
                "country": "Pakistan",
                "postal_code": "74000",
            },
            "fiscal_year_start_month": 1,
            "is_active": True,
        },
    )
    assert updated.status_code == 200
    assert updated.json()["data"]["name"] == "Acme Distribution Pakistan"
    assert updated.json()["data"]["currency"] == "USD"
    assert updated.json()["data"]["country"] == "US"
    assert updated.json()["data"]["ntn"] == "1234567"
    assert updated.json()["data"]["address"]["city"] == "Karachi"
    assert updated.json()["data"]["logo_key"] == f"org-{organization['id']}/acme.png"
    assert updated.json()["data"]["logo_url"].endswith(f"org-{organization['id']}/acme.png")

    customer_login = client.post(
        "/api/v1/auth/login",
        json={"email": "owner@acme.example.com", "password": "owner-password"},
    )
    assert customer_login.status_code == 200
    assert client.post("/api/v1/auth/refresh").status_code == 200

    dashboard = client.get(
        "/api/v1/super-admin/dashboard",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert dashboard.status_code == 200
    dashboard_data = dashboard.json()["data"]
    assert dashboard_data["organizations"] == 1
    assert dashboard_data["new_organizations_30d"] == 1
    assert dashboard_data["tax_identity_organizations"] == 1
    assert dashboard_data["recent_organizations"][0]["id"] == organization["id"]
    assert dashboard_data["recent_organizations"][0]["owner_email"] == "owner@acme.example.com"
    assert sum(point["organizations_created"] for point in dashboard_data["activity_14d"]) == 1
    assert sum(point["customer_logins"] for point in dashboard_data["activity_14d"]) == 1
    assert sum(point["submitted"] for point in dashboard_data["fbr_invoice_activity_14d"]) == 0


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


def test_super_admin_configures_tokens_and_runs_fbr_sandbox_scenarios(
    client: TestClient, db: Session, monkeypatch
):
    monkeypatch.setattr(settings, "FBR_ENCRYPTION_KEY", Fernet.generate_key().decode())
    _cipher.cache_clear()
    _create_admin(db)
    token = _admin_login(client)
    organization = _onboard(client, token)
    org_id = organization["id"]

    missing_token = client.post(
        f"/api/v1/super-admin/organizations/{org_id}/fbr/sandbox-tests",
        headers={"Authorization": f"Bearer {token}"},
        json={"scenario_codes": ["SN001"]},
    )
    assert missing_token.status_code == 400

    configured = client.put(
        f"/api/v1/super-admin/organizations/{org_id}",
        headers={"Authorization": f"Bearer {token}"},
        json={
            "name": "Acme Distribution",
            "currency": "PKR",
            "country": "PK",
            "industry": "Distribution",
            "ntn": "1234567",
            "fiscal_year_start_month": 7,
            "is_active": True,
            "fbr_enabled": True,
            "fbr_environment": "sandbox",
            "fbr_province": "Sindh",
            "fbr_sandbox_token": "sandbox-token",
        },
    )
    assert configured.status_code == 200, configured.text
    assert configured.json()["data"]["fbr_sandbox_configured"] is True
    assert db.get(Organization, org_id).fbr_sandbox_token != "sandbox-token"

    captured_payloads: list[dict] = []

    class FakeFbrClient:
        def __init__(self, token: str, environment):
            assert token == "sandbox-token"
            assert environment.value == "sandbox"

        def post_invoice_with_status(self, payload: dict):
            captured_payloads.append(payload)
            return 200, {
                "invoiceNumber": "SB-123",
                "validationResponse": {"statusCode": "00", "invoiceStatuses": []},
            }

    monkeypatch.setattr("app.super_admin.fbr.service.FbrClient", FakeFbrClient)
    response = client.post(
        f"/api/v1/super-admin/organizations/{org_id}/fbr/sandbox-tests",
        headers={"Authorization": f"Bearer {token}"},
        json={"scenario_codes": ["SN001", "SN002"]},
    )
    assert response.status_code == 200, response.text
    result = response.json()["data"]
    assert result["ok"] is True
    assert result["passed"] == 2
    assert result["failed"] == 0
    assert [payload["scenarioId"] for payload in captured_payloads] == ["SN001", "SN002"]
    assert all(payload["sellerNTNCNIC"] == "1234567" for payload in captured_payloads)
    _cipher.cache_clear()


def test_super_admin_uploads_an_organization_logo(client: TestClient, db: Session, monkeypatch):
    _create_admin(db)
    token = _admin_login(client)
    organization = _onboard(client, token)

    class FakeStorage:
        def save_stream(self, *, org_id, filename, content_type, fileobj, size):
            assert org_id == organization["id"]
            assert filename == "logo.png"
            assert content_type == "image/png"
            assert fileobj.read() == b"logo-bytes"
            assert size == 10
            return StoredFile(
                url="https://cdn.example.com/org-logo.png",
                key=f"org-{org_id}/logo.png",
                filename=filename,
                content_type=content_type,
                size=size,
            )

    monkeypatch.setattr("app.super_admin.media.router.get_storage", lambda: FakeStorage())
    response = client.post(
        f"/api/v1/super-admin/organizations/{organization['id']}/media/upload",
        headers={"Authorization": f"Bearer {token}"},
        files={"file": ("logo.png", b"logo-bytes", "image/png")},
    )
    assert response.status_code == 200, response.text
    assert response.json()["data"]["url"] == "https://cdn.example.com/org-logo.png"


def test_super_admin_updates_owner_password_and_revokes_sessions(client: TestClient, db: Session):
    _create_admin(db)
    admin_token = _admin_login(client)
    organization = _onboard(client, admin_token)

    customer_login = client.post(
        "/api/v1/auth/login",
        json={"email": "owner@acme.example.com", "password": "owner-password"},
    )
    assert customer_login.status_code == 200
    owner = db.query(User).filter(User.email == "owner@acme.example.com").one()
    assert db.query(RefreshSession).filter_by(user_id=owner.id, revoked_at=None).count() == 1

    reset = client.put(
        f"/api/v1/super-admin/organizations/{organization['id']}/owner/password",
        headers={"Authorization": f"Bearer {admin_token}"},
        json={"password": "new-owner-password"},
    )
    assert reset.status_code == 200, reset.text
    assert reset.json()["data"]["owner_email"] == "owner@acme.example.com"
    assert db.query(RefreshSession).filter_by(user_id=owner.id, revoked_at=None).count() == 0

    old_password = client.post(
        "/api/v1/auth/login",
        json={"email": owner.email, "password": "owner-password"},
    )
    assert old_password.status_code == 401
    new_password = client.post(
        "/api/v1/auth/login",
        json={"email": owner.email, "password": "new-owner-password"},
    )
    assert new_password.status_code == 200


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
