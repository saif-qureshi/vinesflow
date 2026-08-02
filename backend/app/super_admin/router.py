from fastapi import APIRouter

from app.super_admin.auth.router import router as auth_router
from app.super_admin.dashboard.router import router as dashboard_router
from app.super_admin.fbr.router import router as fbr_router
from app.super_admin.media.router import router as media_router
from app.super_admin.organizations.router import router as organizations_router

router = APIRouter(prefix="/super-admin")
router.include_router(auth_router)
router.include_router(dashboard_router)
router.include_router(organizations_router)
router.include_router(fbr_router)
router.include_router(media_router)
