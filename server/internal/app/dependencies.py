from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from sqlalchemy.orm import Session
from server.internal.storage.database import get_db
from server.internal.models.db_models import User, UserRole, Role, RolePermission, Permission
from server.internal.app.security import decode_access_token

security = HTTPBearer()

def get_current_user(credentials: HTTPAuthorizationCredentials = Depends(security), db: Session = Depends(get_db)) -> User:
    payload = decode_access_token(credentials.credentials)
    if not payload:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid or expired token")
    
    user_id = payload.get("sub")
    if not user_id:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid token payload")
        
    user = db.query(User).filter(User.id == user_id, User.is_active == True).first()
    if not user:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="User not found or inactive")
    return user

def require_permission(permission_name: str):
    def permission_checker(current_user: User = Depends(get_current_user), db: Session = Depends(get_db)):
        # Собираем все разрешения пользователя через роли
        user_roles = db.query(UserRole).filter(UserRole.user_id == current_user.id).all()
        role_ids = [ur.role_id for ur in user_roles]
        
        allowed_permissions = db.query(RolePermission.permission_id).filter(
            RolePermission.role_id.in_(role_ids)
        ).all()
        allowed_ids = [p[0] for p in allowed_permissions]
        
        # Находим ID нужного разрешения
        perm = db.query(Permission).filter(Permission.name == permission_name).first()
        if not perm or perm.id not in allowed_ids:
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Not enough permissions")
        return current_user
    return permission_checker