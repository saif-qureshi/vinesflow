from __future__ import annotations

from typing import Annotated

from fastapi import APIRouter, Depends, Query

from app.api.deps import require_permission
from app.core.container import Provide
from app.core.pagination import CursorPage
from app.core.responses import EnvelopeRoute
from app.modules.activities.schemas import ActivityListQuery, ActivityRead
from app.modules.activities.service import ActivityService
from app.modules.orgs.models import Membership

router = APIRouter(prefix="/activities", tags=["activities"], route_class=EnvelopeRoute)
Svc = Depends(Provide(ActivityService))


@router.get("", response_model=CursorPage[ActivityRead])
def list_activities(
    query: Annotated[ActivityListQuery, Query()],
    membership: Membership = Depends(require_permission("reports:read")),
    svc: ActivityService = Svc,
):
    items, next_cursor, has_more = svc.list(membership.org_id, query)
    return {"items": items, "next_cursor": next_cursor, "has_more": has_more}
