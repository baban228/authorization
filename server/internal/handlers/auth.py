from fastapi import APIRouter, Depends, HTTPException, status, Query
from fastapi.security import OAuth2PasswordRequestForm
from sqlalchemy.orm import Session
from typing import Optional
from server.internal.storage.database import get_db
from server.internal.models.db_models import User
from server.internal.models.schemas import UserCreate, UserUpdate, UserOut, Token
from server.internal.app.security import get_password_hash, verify_password, create_access_token
from server.internal.app.dependencies import get_current_user

router = APIRouter(prefix="/auth", tags=["auth"])


@router.post("/register", response_model=UserOut, status_code=status.HTTP_201_CREATED, summary="Регистрация нового пользователя")
def register(user_in: UserCreate, db: Session = Depends(get_db)):
    """
    Регистрирует нового пользователя в системе.
    
    Args:
        user_in: Данные пользователя для регистрации (имя, email, пароль).
        db: Сессия базы данных.
        
    Returns:
        UserOut: Данные созданного пользователя (без пароля).
        
    Raises:
        HTTPException 400: Если пользователь с таким email уже существует.
    """
    existing_user = db.query(User).filter(User.email == user_in.email).first()
    if existing_user:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST, 
            detail="Email already registered"
        )
    
    hashed_pwd = get_password_hash(user_in.password)
    
    db_user = User(
        first_name=user_in.first_name,
        last_name=user_in.last_name,
        patronymic=user_in.patronymic,
        email=user_in.email,
        hashed_password=hashed_pwd,
        is_active=True
    )
    
    db.add(db_user)
    db.commit()
    db.refresh(db_user)
    
    return db_user


@router.post("/login", response_model=Token, summary="Вход в систему (OAuth2)")
def login(
    form_data: OAuth2PasswordRequestForm = Depends(),
    db: Session = Depends(get_db),
    redirect_url: Optional[str] = Query(None, description="URL для редиректа после входа"),
    state: Optional[str] = Query(None, description="OAuth2 state parameter")
):
    """
    Аутентификация пользователя по email и паролю через OAuth2 flow.
    
    Использует стандартную форму OAuth2PasswordRequestForm, где поле 'username' интерпретируется как email.
    
    Args:
        form_data: Форма с полями username (email) и password.
        redirect_url: Опциональный URL для редиректа (для OAuth2 клиентов).
        state: Опциональный параметр состояния OAuth2.
        
    Returns:
        Token: JWT access token или объект с токеном и URL редиректа.
        
    Raises:
        HTTPException 401: Если credentials неверны или аккаунт отключен.
        HTTPException 400: Если redirect_url невалиден.
    """
    email = form_data.username
    password = form_data.password
    
    user = db.query(User).filter(User.email == email).first()
    
    if not user or not verify_password(password, user.hashed_password) or not user.is_active:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect email or password, or account is disabled",
            headers={"WWW-Authenticate": "Bearer"},
        )
    
    access_token = create_access_token(data={"sub": str(user.id)})
    
    if redirect_url:
        if not redirect_url.startswith(('http://', 'https://')):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Invalid redirect_url: must start with http:// or https://"
            )
        
        from pydantic import BaseModel
        
        class TokenWithRedirect(BaseModel):
            access_token: str
            token_type: str
            redirect_url: str
            state: Optional[str] = None
        
        return TokenWithRedirect(
            access_token=access_token,
            token_type="bearer",
            redirect_url=redirect_url,
            state=state
        )
    
    return {"access_token": access_token, "token_type": "bearer"}


@router.post("/logout", summary="Выход из системы")
def logout(current_user: User = Depends(get_current_user)):
    """
    Выполняет выход из системы.
    
    Так как используется stateless JWT аутентификация, сервер не хранит сессию.
    Клиент должен самостоятельно удалить токен из локального хранилища.
    Этот эндпоинт служит для подтверждения действия и возможной очистки куки (если используются).
    
    Returns:
        dict: Сообщение об успешном выходе.
    """
    return {"message": "Successfully logged out"}


@router.get("/me", response_model=UserOut, summary="Получить текущий профиль")
def get_profile(current_user: User = Depends(get_current_user)):
    """
    Возвращает данные профиля текущего авторизованного пользователя.
    
    Requires:
        Bearer Token: Valid JWT access token.
        
    Returns:
        UserOut: Данные пользователя (id, имя, email, статус активности).
    """
    return current_user


@router.put("/me", response_model=UserOut, summary="Обновить профиль")
def update_profile(
    user_update: UserUpdate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Обновляет данные профиля текущего пользователя.
    
    Можно обновить имя, фамилию, отчество, email или пароль.
    Пароль автоматически хэшируется перед сохранением.
    
    Args:
        user_update: Объект с новыми данными (только измененные поля).
        current_user: Текущий авторизованный пользователь.
        db: Сессия базы данных.
        
    Returns:
        UserOut: Обновленные данные пользователя.
    """
    for field, value in user_update.model_dump(exclude_unset=True).items():
        if field == "password":
            value = get_password_hash(value)

        setattr(current_user, field, value)
    
    db.commit()
    db.refresh(current_user)
    
    return current_user


@router.delete("/me", status_code=status.HTTP_204_NO_CONTENT, summary="Удалить аккаунт (мягкое удаление)")
def soft_delete_account(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Выполняет мягкое удаление аккаунта текущего пользователя.
    
    Аккаунт помечается как неактивный (is_active=False).
    Данные сохраняются в базе для аудита или восстановления, но вход в систему становится невозможным.
    
    Raises:
        HTTPException 401: Если пользователь не авторизован (обрабатывается зависимостью get_current_user).
        
    Returns:
        No Content (204): Успешное выполнение операции без тела ответа.
    """
    current_user.is_active = False
    db.commit()
