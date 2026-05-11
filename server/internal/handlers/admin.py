from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from server.internal.storage.database import get_db
from server.internal.models.db_models import User, Role, Permission, UserRole, RolePermission
from server.internal.app.dependencies import require_permission

router = APIRouter(prefix="/admin", tags=["admin"])


@router.get("/roles", summary="Получить список всех ролей")
def list_roles(
    db: Session = Depends(get_db), 
    _=Depends(require_permission("manage:roles"))
):
    """
    Возвращает список всех доступных ролей в системе.
    
    Требуется разрешение: manage:roles
    
    Returns:
        List[Role]: Список объектов ролей.
    """
    return db.query(Role).all()


@router.post("/roles", summary="Создать новую роль", status_code=status.HTTP_201_CREATED)
def create_role(
    name: str, 
    db: Session = Depends(get_db), 
    _=Depends(require_permission("manage:roles"))
):
    """
    Создает новую роль с указанным именем.
    
    Args:
        name: Уникальное имя новой роли (например, "moderator").
        
    Returns:
        Role: Созданный объект роли.
        
    Raises:
        HTTPException 400: Если роль с таким именем уже существует.
    """
    existing_role = db.query(Role).filter(Role.name == name).first()
    if existing_role:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST, 
            detail=f"Role '{name}' already exists"
        )

    role = Role(name=name)
    db.add(role)
    db.commit()
    db.refresh(role)
    return role


@router.post("/permissions", summary="Создать новое разрешение", status_code=status.HTTP_201_CREATED)
def create_permission(
    name: str, 
    db: Session = Depends(get_db), 
    _=Depends(require_permission("manage:roles"))
):
    """
    Создает новое разрешение (permission) в системе.
    
    Разрешения используются для контроля доступа к ресурсам (например, "read:users").
    
    Args:
        name: Уникальное имя разрешения (формат обычно action:resource).
        
    Returns:
        Permission: Созданный объект разрешения.
        
    Raises:
        HTTPException 400: Если разрешение с таким именем уже существует.
    """
    existing_perm = db.query(Permission).filter(Permission.name == name).first()
    if existing_perm:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST, 
            detail=f"Permission '{name}' already exists"
        )
    
    perm = Permission(name=name)
    db.add(perm)
    db.commit()
    db.refresh(perm)
    return perm


@router.post("/assign-role", summary="Назначить роль пользователю")
def assign_role(
    user_id: int, 
    role_name: str, 
    db: Session = Depends(get_db), 
    _=Depends(require_permission("manage:roles"))
):
    """
    Назначает указанную роль конкретному пользователю.
    
    Args:
        user_id: ID пользователя, которому назначается роль.
        role_name: Имя роли, которую нужно назначить.
        
    Returns:
        dict: Сообщение об успешном назначении.
        
    Raises:
        HTTPException 404: Если пользователь или роль не найдены.
        HTTPException 400: Если роль уже назначена этому пользователю.
    """
    user = db.query(User).filter(User.id == user_id).first()
    role = db.query(Role).filter(Role.name == role_name).first()
    
    if not user:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="User not found")
    if not role:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Role not found")
    
    existing_assignment = db.query(UserRole).filter(
        UserRole.user_id == user.id, 
        UserRole.role_id == role.id
    ).first()
    
    if existing_assignment:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST, 
            detail=f"Role '{role_name}' is already assigned to user {user_id}"
        )
        
    db.add(UserRole(user_id=user.id, role_id=role.id))
    db.commit()
    
    return {"message": f"Role '{role_name}' successfully assigned to user {user_id}"}


@router.post("/grant-permission", summary="Предоставить разрешение роли")
def grant_permission(
    role_name: str, 
    permission_name: str, 
    db: Session = Depends(get_db), 
    _=Depends(require_permission("manage:roles"))
):
    """
    Предоставляет указанное разрешение конкретной роли.
    
    Все пользователи с этой ролью автоматически получат это разрешение.
    
    Args:
        role_name: Имя роли, которой предоставляется право.
        permission_name: Имя разрешения, которое предоставляется.
        
    Returns:
        dict: Сообщение об успешном предоставлении права.
        
    Raises:
        HTTPException 404: Если роль или разрешение не найдены.
        HTTPException 400: Если разрешение уже предоставлено этой роли.
    """
    role = db.query(Role).filter(Role.name == role_name).first()
    perm = db.query(Permission).filter(Permission.name == permission_name).first()
    
    if not role:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Role not found")
    if not perm:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Permission not found")
        
    existing_link = db.query(RolePermission).filter(
        RolePermission.role_id == role.id, 
        RolePermission.permission_id == perm.id
    ).first()
    
    if existing_link:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST, 
            detail=f"Permission '{permission_name}' is already granted to role '{role_name}'"
        )
        
    db.add(RolePermission(role_id=role.id, permission_id=perm.id))
    db.commit()
    
    return {"message": f"Permission '{permission_name}' successfully granted to role '{role_name}'"}