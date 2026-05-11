from fastapi import APIRouter, Depends
from server.internal.app.dependencies import require_permission

router = APIRouter(prefix="/resources", tags=["resources"])

@router.get("/public")
def public_resource():
    return {"data": "Available to everyone"}

@router.get("/protected")
def protected_resource(_=Depends(require_permission("read:own_profile"))):
    return {"data": "You have read:own_profile permission"}

@router.get("/admin-only")
def admin_resource(_=Depends(require_permission("manage:roles"))):
    return {"data": "Welcome, admin!"}