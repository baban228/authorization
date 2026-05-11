from fastapi import APIRouter, Depends
from server.internal.app.dependencies import require_permission

router = APIRouter(prefix="/resources", tags=["resources"])


@router.get("/public", summary="Публичный ресурс")
def public_resource():
    """
    Эндпоинт, доступный всем пользователям без аутентификации.
    
    Не требует заголовка Authorization или наличия токена.
    Используется для проверки работоспособности API или получения общей информации.
    
    Returns:
        dict: Публичные данные.
    """
    return {"data": "Available to everyone"}


@router.get("/protected", summary="Защищенный ресурс (Требует прав read:own_profile)")
def protected_resource(_=Depends(require_permission("read:own_profile"))):
    """
    Эндпоинт, доступный только авторизованным пользователям с разрешением 'read:own_profile'.
    
    Зависимость require_permission выполняет две проверки:
    1. get_current_user: Проверяет валидность JWT токена и активность пользователя (401 если не ок).
    2. Проверка прав: Ищет разрешение 'read:own_profile' в ролях пользователя (403 если нет прав).
    
    Обычно это разрешение есть у всех зарегистрированных пользователей (роль 'user').
    
    Requires:
        Bearer Token: Valid JWT access token.
        Permission: read:own_profile
        
    Returns:
        dict: Защищенные данные.
        
    Raises:
        HTTPException 401: Если токен отсутствует или невалиден.
        HTTPException 403: Если у пользователя нет права read:own_profile.
    """
    return {"data": "You have read:own_profile permission"}


@router.get("/admin-only", summary="Админский ресурс (Требует прав manage:roles)")
def admin_resource(_=Depends(require_permission("manage:roles"))):
    """
    Эндпоинт, доступный исключительно администраторам системы.
    
    Требует наличия разрешения 'manage:roles', которое обычно привязано только к роли 'admin'.
    Обычные пользователи получат ошибку 403 Forbidden.
    
    Requires:
        Bearer Token: Valid JWT access token.
        Role: admin (или любая роль с правом manage:roles).
        
    Returns:
        dict: Данные, доступные только администраторам.
        
    Raises:
        HTTPException 401: Если токен отсутствует или невалиден.
        HTTPException 403: Если у пользователя нет права manage:roles.
    """
    return {"data": "Welcome, admin!"}