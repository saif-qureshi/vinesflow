from fastapi import APIRouter

from app.modules.accounting.router import router as accounting_router
from app.modules.activities.router import router as activities_router
from app.modules.auth.router import router as auth_router
from app.modules.categories.router import router as categories_router
from app.modules.dashboard.router import router as dashboard_router
from app.modules.documents.router import router as documents_router
from app.modules.expenses.router import router as expenses_router
from app.modules.fbr.router import router as fbr_router
from app.modules.inventory.router import router as inventory_router
from app.modules.locations.router import router as locations_router
from app.modules.media.router import router as media_router
from app.modules.orgs.router import router as orgs_router
from app.modules.parties.router import router as parties_router
from app.modules.payments.router import router as payments_router
from app.modules.products.router import router as products_router
from app.modules.rbac.router import router as rbac_router
from app.modules.reports.router import router as reports_router
from app.modules.settings.router import router as settings_router
from app.modules.uoms.router import router as uoms_router
from app.modules.users.router import router as users_router

api_router = APIRouter()
api_router.include_router(auth_router)
api_router.include_router(users_router)
api_router.include_router(orgs_router)
api_router.include_router(rbac_router)
api_router.include_router(products_router)
api_router.include_router(parties_router)
api_router.include_router(locations_router)
api_router.include_router(inventory_router)
api_router.include_router(documents_router)
api_router.include_router(fbr_router)
api_router.include_router(payments_router)
api_router.include_router(expenses_router)
api_router.include_router(activities_router)
api_router.include_router(categories_router)
api_router.include_router(dashboard_router)
api_router.include_router(uoms_router)
api_router.include_router(media_router)
api_router.include_router(settings_router)
api_router.include_router(accounting_router)
api_router.include_router(reports_router)
