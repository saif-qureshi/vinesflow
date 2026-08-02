from __future__ import annotations

import json
from copy import deepcopy
from datetime import UTC, date, datetime
from functools import lru_cache
from pathlib import Path
from typing import Any

from sqlalchemy.orm import Session

from app.core.crypto import decrypt_secret
from app.core.exceptions import BadRequestError, NotFoundError, ServiceUnavailableError
from app.modules.fbr.client import FbrClient
from app.modules.fbr.enums import FbrEnvironment
from app.modules.orgs.models import Organization
from app.super_admin.fbr.schemas import (
    FBR_SANDBOX_SCENARIOS,
    SuperAdminFbrSandboxScenarioResult,
    SuperAdminFbrSandboxTestRequest,
    SuperAdminFbrSandboxTestResult,
)


@lru_cache
def _fixtures() -> dict[str, dict[str, Any]]:
    path = Path(__file__).with_name("fbr_sandbox_scenarios.json")
    return json.loads(path.read_text())


class SuperAdminFbrService:
    def __init__(self, db: Session) -> None:
        self.db = db

    def run_sandbox_tests(
        self, org_id: int, payload: SuperAdminFbrSandboxTestRequest
    ) -> SuperAdminFbrSandboxTestResult:
        org = self.db.get(Organization, org_id)
        if org is None:
            raise NotFoundError("Organization not found")
        if not org.fbr_sandbox_token:
            raise BadRequestError("No FBR sandbox token is configured for this organization")
        token = decrypt_secret(org.fbr_sandbox_token)
        if not token:
            raise BadRequestError("The configured FBR sandbox token could not be decrypted")

        client = FbrClient(token, FbrEnvironment.SANDBOX)
        started_at = datetime.now(UTC)
        results = [self._run_scenario(client, org, code) for code in payload.scenario_codes]
        completed_at = datetime.now(UTC)
        passed = sum(result.status == "passed" for result in results)
        return SuperAdminFbrSandboxTestResult(
            ok=passed == len(results),
            total=len(results),
            passed=passed,
            failed=len(results) - passed,
            scenarios=results,
            started_at=started_at,
            completed_at=completed_at,
        )

    def _run_scenario(
        self, client: FbrClient, org: Organization, code: str
    ) -> SuperAdminFbrSandboxScenarioResult:
        fixture = _fixtures().get(code)
        if fixture is None:
            raise BadRequestError(f"FBR sandbox fixture is missing for {code}")
        payload = self._prepare_payload(code, fixture, org)
        try:
            http_status, response = client.post_invoice_with_status(payload)
        except ServiceUnavailableError as exc:
            return SuperAdminFbrSandboxScenarioResult(
                code=code,
                label=FBR_SANDBOX_SCENARIOS[code],
                status="failed",
                errors=[exc.message],
            )

        body = response if isinstance(response, dict) else {}
        validation = body.get("validationResponse")
        validation = validation if isinstance(validation, dict) else {}
        raw_status = validation.get("statusCode")
        fbr_status = str(raw_status) if raw_status is not None else None
        errors = self._validation_errors(validation)
        passed = http_status == 200 and (fbr_status == "00" or validation.get("status") == "Valid")
        if not passed and not errors:
            errors = [f"FBR returned status {fbr_status or http_status}"]
        invoice_number = (
            body.get("invoiceNumber")
            or body.get("invoiceNo")
            or validation.get("invoiceNumber")
            or validation.get("invoiceNo")
        )
        return SuperAdminFbrSandboxScenarioResult(
            code=code,
            label=FBR_SANDBOX_SCENARIOS[code],
            status="passed" if passed else "failed",
            http_status_code=http_status,
            fbr_status_code=fbr_status,
            invoice_number=str(invoice_number) if invoice_number else None,
            errors=errors,
        )

    @staticmethod
    def _validation_errors(validation: dict[str, Any]) -> list[str]:
        errors: list[str] = []
        if validation.get("error"):
            errors.append(str(validation["error"]))
        statuses = validation.get("invoiceStatuses")
        for item in statuses if isinstance(statuses, list) else []:
            if not isinstance(item, dict) or not item.get("error"):
                continue
            item_number = item.get("itemSNo")
            error = str(item["error"])
            errors.append(f"Item {item_number}: {error}" if item_number else error)
        return list(dict.fromkeys(errors))

    @staticmethod
    def _prepare_payload(code: str, fixture: dict[str, Any], org: Organization) -> dict[str, Any]:
        payload = deepcopy(fixture)
        address = org.address if isinstance(org.address, dict) else {}
        address_text = ", ".join(
            str(value)
            for value in (address.get("line1"), address.get("line2"), address.get("city"))
            if value
        )
        payload["scenarioId"] = code
        payload["invoiceDate"] = date.today().isoformat()
        payload["invoiceRefNo"] = f"SB-{code}-{datetime.now(UTC).strftime('%Y%m%d%H%M%S%f')}"
        payload["sellerBusinessName"] = org.name
        payload["sellerNTNCNIC"] = (
            org.cnic or org.ntn or org.strn or payload.get("sellerNTNCNIC", "")
        )
        if address_text:
            payload["sellerAddress"] = address_text
        if org.fbr_province or address.get("state"):
            payload["sellerProvince"] = org.fbr_province or address["state"]
        return payload
