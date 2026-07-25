from __future__ import annotations

from typing import Any

import httpx

from app.core.config import settings
from app.core.exceptions import ServiceUnavailableError
from app.modules.fbr.enums import FbrEnvironment
from app.modules.fbr.jsonrepair import loads as _json_loads

REFERENCE_ENDPOINTS = {
    "doc_types": "/pdi/v1/doctypecode",
    "hs_codes": "/pdi/v1/itemdesccode",
    "uoms": "/pdi/v1/uom",
    "sale_types": "/pdi/v1/transtypecode",
    "sro_item_codes": "/pdi/v1/sroitemcode",
    "sro_schedule": "/pdi/v1/SroSchedule",
    "sale_type_to_rate": "/pdi/v2/SaleTypeToRate",
    "sro_item": "/pdi/v2/SROItem",
}

INVOICE_ENDPOINTS = {
    "post": "/di_data/v1/di/postinvoicedata",
    "validate": "/di_data/v1/di/validateinvoicedata",
}

FBR_TOKEN_REJECTED = (
    "FBR rejected the sign-in token for this environment. "
    "Check the FBR token and seller registration number in Settings → Organization → FBR."
)


def _decode(response: httpx.Response) -> Any:
    try:
        return _json_loads(response.text)
    except ValueError as exc:
        sample = (response.text or "").strip()[:300]
        raise ServiceUnavailableError(f"FBR returned an unreadable response: {sample}") from exc


def _fbr_reason(response: httpx.Response) -> str:
    try:
        body = _json_loads(response.text)
    except ValueError:
        return (response.text or "").strip()[:300]
    if isinstance(body, dict):
        vr = body.get("validationResponse")
        if isinstance(vr, dict) and vr.get("error"):
            return str(vr["error"])
        for key in ("error", "message", "Message"):
            if body.get(key):
                return str(body[key])
    return (response.text or "").strip()[:300]


def _unauthorized(response: httpx.Response) -> ServiceUnavailableError:
    reason = _fbr_reason(response)
    return ServiceUnavailableError(f"FBR: {reason}" if reason else FBR_TOKEN_REJECTED)


class FbrClient:
    def __init__(self, token: str, environment: FbrEnvironment = FbrEnvironment.PRODUCTION) -> None:
        self.token = token
        self.environment = environment
        self.base_url = settings.FBR_BASE_URL.rstrip("/")

    @property
    def _headers(self) -> dict[str, str]:
        return {"Authorization": f"Bearer {self.token}", "Content-Type": "application/json"}

    def get(self, endpoint: str, params: dict[str, Any] | None = None, timeout: float = 60.0) -> Any:
        try:
            response = httpx.get(
                f"{self.base_url}{endpoint}", params=params, headers=self._headers, timeout=timeout
            )
        except httpx.HTTPError as exc:
            raise ServiceUnavailableError("FBR service is unavailable") from exc
        if response.status_code == 401:
            raise _unauthorized(response)
        if response.status_code != 200:
            raise ServiceUnavailableError(f"FBR returned {response.status_code}")
        return _decode(response)

    def _post(self, endpoint: str, payload: dict) -> Any:
        target = endpoint if self.environment == FbrEnvironment.PRODUCTION else f"{endpoint}_sb"
        try:
            response = httpx.post(
                f"{self.base_url}{target}", json=payload, headers=self._headers, timeout=90.0
            )
        except httpx.HTTPError as exc:
            raise ServiceUnavailableError("FBR service is unavailable") from exc
        if response.status_code == 401:
            raise _unauthorized(response)
        return _decode(response)

    def hs_uom(self, hs_code: str) -> Any:
        return self.get(
            "/pdi/v2/HS_UOM", params={"hs_code": hs_code, "annexure_id": 3}, timeout=12.0
        )

    def sro_items(self, sro_id: str, on_date: str) -> Any:
        return self.get(
            "/pdi/v2/SROItem", params={"sro_id": sro_id, "date": on_date}, timeout=12.0
        )

    def validate_invoice(self, payload: dict) -> Any:
        return self._post(INVOICE_ENDPOINTS["validate"], payload)

    def post_invoice(self, payload: dict) -> Any:
        return self._post(INVOICE_ENDPOINTS["post"], payload)
