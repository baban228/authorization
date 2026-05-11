from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from sqlalchemy.orm import Session
from server.internal.storage.database import get_db
from server.internal.models.db_models import User, UserRole, Role, RolePermission, Permission
from server.internal.app.security import decode_access_token

security = HTTPBearer()


def get_current_user(
    credentials: HTTPAuthorizationCredentials = Depends(security), 
    db: Session = Depends(get_db)
) -> User:
    """
    Зависимость для получения текущего авторизованного пользователя.
    
    Извлекает JWT токен из заголовка Authorization, проверяет его валидность
    и наличие пользователя в базе данных со статусом is_active=True.
    
    Args:
        credentials: Данные аутентификации из заголовка (Bearer token).
        db: Сессия базы данных.
        
    Returns:
        User: Объект текущего активного пользователя.
        
    Raises:
        HTTPException 401: Если токен отсутствует, невалиден, истек или пользователь не найден/неактивен.
    """
    payload = decode_access_token(credentials.credentials)
    
    if not payload:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or expired token",
            headers={"WWW-Authenticate": "Bearer"},
        )

    user_id = payload.get("sub")
    if not user_id:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid token payload: missing user id",
            headers={"WWW-Authenticate": "Bearer"},
        )
        
    user = db.query(User).filter(User.id == user_id, User.is_active == True).first()
    
    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="User not found or account is inactive/deleted",
            headers={"WWW-Authenticate": "Bearer"},
        )
        
    return user


def require_permission(permission_name: str):
    """
    Фабрика зависимостей для проверки прав доступа (RBAC).
    
    Создает зависимость, которая проверяет, есть ли у текущего пользователя
    указанное разрешение (permission) через его роли.
    
    Args:
        permission_name: Строковое имя требуемого разрешения (например, "read:users").
        
    Returns:
        Callable: Зависимость FastAPI, которую можно использовать в Depends().
        
    Raises:
        HTTPException 403: Если у пользователя нет требуемого разрешения.
    """
    def permission_checker(
        current_user: User = Depends(get_current_user), 
        db: Session = Depends(get_db)
    ):
        """
        Внутренняя функция-чекер прав доступа.
        
        Проверяет наличие конкретного разрешения у текущего пользователя.
        Логика: Пользователь -> Роли -> Разрешения ролей -> Проверка наличия нужного разрешения.
        """
        user_roles = db.query(UserRole).filter(UserRole.user_id == current_user.id).all()

        if not user_roles:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="User has no roles assigned"
            )

        role_ids = [ur.role_id for ur in user_roles]
     
        allowed_permissions = db.query(RolePermission.permission_id).filter(
            RolePermission.role_id.in_(role_ids)
        ).all()
        
        allowed_ids = [p[0] for p in allowed_permissions]

        perm = db.query(Permission).filter(Permission.name == permission_name).first()

        if not perm or perm.id not in allowed_ids:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"Not enough permissions. Required: '{permission_name}'"
            )
        return current_user
        
    return permission_checker