from __future__ import annotations

from app.modules.accounting.constants import DEFAULT_ACCOUNTS

BASE = "/api/v1/accounting"


def _ctx(register, org_id_of, h):
    token = register()
    return h(token, org_id_of(token))


def test_seeded_chart_exposed(client, register, org_id_of, h):
    headers = _ctx(register, org_id_of, h)
    res = client.get(f"{BASE}/accounts", headers=headers)
    assert res.status_code == 200, res.text
    accounts = res.json()["data"]
    assert len(accounts) == len(DEFAULT_ACCOUNTS)
    codes = {a["code"] for a in accounts}
    assert {"1130", "4100", "5100"} <= codes
    ar = next(a for a in accounts if a["code"] == "1130")
    assert ar["is_control_account"] is True


def test_fiscal_year_and_periods_seeded(client, register, org_id_of, h):
    headers = _ctx(register, org_id_of, h)
    years = client.get(f"{BASE}/fiscal-years", headers=headers).json()["data"]
    assert len(years) == 1
    assert years[0]["status"] == "active"
    periods = client.get(f"{BASE}/periods", headers=headers).json()["data"]
    assert len(periods) == 12


def test_create_next_fiscal_year(client, register, org_id_of, h):
    headers = _ctx(register, org_id_of, h)
    before = client.get(f"{BASE}/fiscal-years", headers=headers).json()["data"]
    assert len(before) == 1

    res = client.post(f"{BASE}/fiscal-years", headers=headers)
    assert res.status_code == 201, res.text

    after = client.get(f"{BASE}/fiscal-years", headers=headers).json()["data"]
    assert len(after) == 2
    assert after[1]["starts_on"] > after[0]["ends_on"]
    periods = client.get(f"{BASE}/periods", headers=headers).json()["data"]
    assert len(periods) == 24


def test_delete_fiscal_year(client, register, org_id_of, h):
    headers = _ctx(register, org_id_of, h)
    years = client.get(f"{BASE}/fiscal-years", headers=headers).json()["data"]
    only = client.delete(f"{BASE}/fiscal-years/{years[0]['id']}", headers=headers)
    assert only.status_code == 409  # can't delete the only fiscal year

    client.post(f"{BASE}/fiscal-years", headers=headers)
    years = client.get(f"{BASE}/fiscal-years", headers=headers).json()["data"]
    assert len(years) == 2

    res = client.delete(f"{BASE}/fiscal-years/{years[1]['id']}", headers=headers)
    assert res.status_code == 204
    assert len(client.get(f"{BASE}/fiscal-years", headers=headers).json()["data"]) == 1
    assert len(client.get(f"{BASE}/periods", headers=headers).json()["data"]) == 12


def test_create_custom_account_and_reject_duplicate(client, register, org_id_of, h):
    headers = _ctx(register, org_id_of, h)
    body = {
        "code": "5210",
        "name": "Rent",
        "account_type": "expense",
        "normal_balance": "debit",
    }
    res = client.post(f"{BASE}/accounts", json=body, headers=headers)
    assert res.status_code == 201, res.text
    created = res.json()["data"]
    assert created["code"] == "5210"
    assert created["is_control_account"] is False

    dup = client.post(f"{BASE}/accounts", json=body, headers=headers)
    assert dup.status_code == 409


def test_update_account_name(client, register, org_id_of, h):
    headers = _ctx(register, org_id_of, h)
    accounts = client.get(f"{BASE}/accounts", headers=headers).json()["data"]
    opex = next(a for a in accounts if a["code"] == "5200")
    res = client.patch(f"{BASE}/accounts/{opex['id']}", json={"name": "Overheads"}, headers=headers)
    assert res.status_code == 200, res.text
    assert res.json()["data"]["name"] == "Overheads"


def test_lock_and_reopen_period(client, register, org_id_of, h):
    headers = _ctx(register, org_id_of, h)
    periods = client.get(f"{BASE}/periods", headers=headers).json()["data"]
    period_id = periods[0]["id"]

    locked = client.patch(
        f"{BASE}/periods/{period_id}/status", json={"status": "locked"}, headers=headers
    )
    assert locked.status_code == 200, locked.text
    assert locked.json()["data"]["status"] == "locked"

    reopened = client.patch(
        f"{BASE}/periods/{period_id}/status", json={"status": "open"}, headers=headers
    )
    assert reopened.json()["data"]["status"] == "open"
