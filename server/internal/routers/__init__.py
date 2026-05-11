from fastapi import APIRouter
from server.internal.handlers.auth import router as auth_router
from server.internal.handlers.admin import router as admin_router
from server.internal.handlers.resources import router as resources_router

api_router = APIRouter()
api_router.include_router(auth_router)
api_router.include_router(admin_router)
api_router.include_router(resources_router)