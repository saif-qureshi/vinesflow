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


def _codes(client, headers):
    accounts = client.get(f"{BASE}/accounts", headers=headers).json()["data"]
    return {a["code"]: a["id"] for a in accounts}


def test_manual_journal_draft_edit_post_reverse(client, register, org_id_of, h):
    headers = _ctx(register, org_id_of, h)
    code = _codes(client, headers)
    body = {
        "date": "2026-07-15",
        "reference_no": "ADJ-99",
        "description": "Reclass office expense",
        "lines": [
            {"account_id": code["5200"], "debit": "100", "credit": "0"},
            {"account_id": code["1110"], "debit": "0", "credit": "100"},
        ],
    }
    res = client.post(f"{BASE}/vouchers", json=body, headers=headers)
    assert res.status_code == 201, res.text
    voucher = res.json()["data"]
    assert voucher["status"] == "draft"  # created as a draft, not posted
    assert voucher["number"].startswith("JV")
    assert voucher["reference_no"] == "ADJ-99"
    vid = voucher["id"]

    body["description"] = "Reclass office rent"
    upd = client.patch(f"{BASE}/vouchers/{vid}", json=body, headers=headers)
    assert upd.status_code == 200
    assert upd.json()["data"]["description"] == "Reclass office rent"

    posted = client.post(f"{BASE}/vouchers/{vid}/post", headers=headers)
    assert posted.status_code == 200
    assert posted.json()["data"]["status"] == "posted"

    rev = client.post(f"{BASE}/vouchers/{vid}/reverse", headers=headers)
    assert rev.status_code == 200
    assert rev.json()["data"]["number"].startswith("RV")


def test_opening_balances_post_and_balance_to_obe(client, register, org_id_of, h):
    headers = _ctx(register, org_id_of, h)
    code = _codes(client, headers)
    body = {
        "date": "2026-07-01",
        "entries": [
            {"account_id": code["1110"], "debit": "50000", "credit": "0"},  # Cash
            {"account_id": code["1130"], "debit": "80000", "credit": "0"},  # AR (control)
            {"account_id": code["2110"], "debit": "0", "credit": "60000"},  # AP (control)
        ],
    }
    res = client.post(f"{BASE}/opening-balances", json=body, headers=headers)
    assert res.status_code == 201, res.text
    voucher = res.json()["data"]
    assert voucher["voucher_type"] == "opening"
    assert voucher["status"] == "posted"
    # net debit 70000 → balanced by an Opening Balance Equity credit
    assert float(voucher["total_debit"]) == float(voucher["total_credit"])

    dup = client.post(f"{BASE}/opening-balances", json=body, headers=headers)
    assert dup.status_code == 409  # can only set opening balances once


def test_opening_balances_reject_manual_inventory_value(client, register, org_id_of, h):
    headers = _ctx(register, org_id_of, h)
    code = _codes(client, headers)
    res = client.post(
        f"{BASE}/opening-balances",
        headers=headers,
        json={
            "date": "2026-07-01",
            "entries": [
                {"account_id": code["1140"], "debit": "1000", "credit": "0"},
                {"account_id": code["3300"], "debit": "0", "credit": "1000"},
            ],
        },
    )
    assert res.status_code == 400
    assert "item opening stock" in res.json()["error"]["message"]


def test_stock_opening_does_not_block_other_account_opening_balances(
    client, register, org_id_of, h
):
    headers = _ctx(register, org_id_of, h)
    code = _codes(client, headers)
    uoms = client.get("/api/v1/uoms", headers=headers).json()["data"]
    uom_id = next(uom["id"] for uom in uoms if uom["symbol"] == "pc")
    product_id = client.post(
        "/api/v1/products",
        headers=headers,
        json={"name": "Opening item", "uom_id": uom_id, "track_inventory": True},
    ).json()["data"]["id"]
    location_id = client.get("/api/v1/locations", headers=headers).json()["data"][0]["id"]
    stock = client.post(
        "/api/v1/inventory/opening",
        headers=headers,
        json={
            "product_id": product_id,
            "date": "2026-07-01",
            "entries": [{"location_id": location_id, "quantity": 5, "unit_cost": 100}],
        },
    )
    assert stock.status_code == 200, stock.text

    balances = client.post(
        f"{BASE}/opening-balances",
        headers=headers,
        json={
            "date": "2026-07-01",
            "entries": [{"account_id": code["1110"], "debit": "1000", "credit": "0"}],
        },
    )
    assert balances.status_code == 201, balances.text
    assert balances.json()["data"]["source_type"] == "opening_balances"


def test_manual_journal_cancel_draft(client, register, org_id_of, h):
    headers = _ctx(register, org_id_of, h)
    code = _codes(client, headers)
    body = {
        "date": "2026-07-15",
        "lines": [
            {"account_id": code["5200"], "debit": "50"},
            {"account_id": code["1110"], "credit": "50"},
        ],
    }
    vid = client.post(f"{BASE}/vouchers", json=body, headers=headers).json()["data"]["id"]
    res = client.post(f"{BASE}/vouchers/{vid}/cancel", headers=headers)
    assert res.status_code == 200
    assert res.json()["data"]["status"] == "cancelled"


def test_manual_journal_unbalanced_rejected(client, register, org_id_of, h):
    headers = _ctx(register, org_id_of, h)
    code = _codes(client, headers)
    body = {
        "date": "2026-07-15",
        "lines": [
            {"account_id": code["5200"], "debit": "100"},
            {"account_id": code["1110"], "credit": "90"},
        ],
    }
    assert client.post(f"{BASE}/vouchers", json=body, headers=headers).status_code == 400


def test_manual_journal_to_control_account_rejected(client, register, org_id_of, h):
    headers = _ctx(register, org_id_of, h)
    code = _codes(client, headers)
    body = {
        "date": "2026-07-15",
        "lines": [
            {"account_id": code["1130"], "debit": "100"},  # AR is a control account
            {"account_id": code["1110"], "credit": "100"},
        ],
    }
    assert client.post(f"{BASE}/vouchers", json=body, headers=headers).status_code == 400


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
