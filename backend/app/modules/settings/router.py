from __future__ import annotations

from fastapi import APIRouter, Depends

from app.api.deps import require_permission
from app.core.container import Provide
from app.core.responses import EnvelopeRoute
from app.modules.orgs.models import Membership
from app.modules.settings.schemas import NumberingEntry, NumberingUpdate
from app.modules.settings.service import SettingsService

router = APIRouter(prefix="/settings", tags=["settings"], route_class=EnvelopeRoute)
Svc = Depends(Provide(SettingsService))


@router.get("/numbering", response_model=list[NumberingEntry])
def get_numbering(
    membership: Membership = Depends(require_permission("orgs:read")),
    svc: SettingsService = Svc,
):
    return svc.numbering_entries(membership.org_id)


@router.put("/numbering", response_model=list[NumberingEntry])
def update_numbering(
    payload: NumberingUpdate,
    membership: Membership = Depends(require_permission("orgs:update")),
    svc: SettingsService = Svc,
):
    return svc.set_numbering(membership.org_id, payload.entries)


@router.get("/{group}", response_model=dict)
def get_settings_group(
    group: str,
    membership: Membership = Depends(require_permission("orgs:read")),
    svc: SettingsService = Svc,
):
    return svc.get_group(membership.org_id, group)


@router.put("/{group}", response_model=dict)
def set_settings_group(
    group: str,
    values: dict,
    membership: Membership = Depends(require_permission("orgs:update")),
    svc: SettingsService = Svc,
):
    return svc.set_group(membership.org_id, group, values)
