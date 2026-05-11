from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from server.internal.storage.database import get_db
from server.internal.models.db_models import User, Role, Permission, UserRole, RolePermission
from server.internal.app.dependencies import require_permission

router = APIRouter(prefix="/admin", tags=["admin"])

@router.get("/roles")
def list_roles(db: Session = Depends(get_db), _=Depends(require_permission("manage:roles"))):
    return db.query(Role).all()

@router.post("/roles")
def create_role(name: str, db: Session = Depends(get_db), _=Depends(require_permission("manage:roles"))):
    if db.query(Role).filter(Role.name == name).first():
        raise HTTPException(400, "Role exists")
    role = Role(name=name)
    db.add(role)
    db.commit()
    return role

@router.post("/permissions")
def create_permission(name: str, db: Session = Depends(get_db), _=Depends(require_permission("manage:roles"))):
    if db.query(Permission).filter(Permission.name == name).first():
        raise HTTPException(400, "Permission exists")
    perm = Permission(name=name)
    db.add(perm)
    db.commit()
    return perm

@router.post("/assign-role")
def assign_role(user_id: int, role_name: str, db: Session = Depends(get_db), _=Depends(require_permission("manage:roles"))):
    user = db.query(User).filter(User.id == user_id).first()
    role = db.query(Role).filter(Role.name == role_name).first()
    if not user or not role:
        raise HTTPException(404, "User or Role not found")
    
    existing = db.query(UserRole).filter(UserRole.user_id == user.id, UserRole.role_id == role.id).first()
    if existing:
        raise HTTPException(400, "Role already assigned")
        
    db.add(UserRole(user_id=user.id, role_id=role.id))
    db.commit()
    return {"message": "Role assigned"}

@router.post("/grant-permission")
def grant_permission(role_name: str, permission_name: str, db: Session = Depends(get_db), _=Depends(require_permission("manage:roles"))):
    role = db.query(Role).filter(Role.name == role_name).first()
    perm = db.query(Permission).filter(Permission.name == permission_name).first()
    if not role or not perm:
        raise HTTPException(404, "Role or Permission not found")
        
    existing = db.query(RolePermission).filter(RolePermission.role_id == role.id, RolePermission.permission_id == perm.id).first()
    if existing:
        raise HTTPException(400, "Permission already granted")
        
    db.add(RolePermission(role_id=role.id, permission_id=perm.id))
    db.commit()
    return {"message": "Permission granted"}