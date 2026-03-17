"""
API v1 Router - Aggregates all v1 endpoint routers.
"""

from fastapi import APIRouter

from app.api.v1.leads import router as leads_router
from app.api.v1.tags import router as tags_router

api_router = APIRouter()

api_router.include_router(leads_router, prefix="/leads", tags=["Leads"])
api_router.include_router(tags_router, prefix="/tags", tags=["Tags"])
