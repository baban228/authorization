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

@router.post("/register", response_model=UserOut, status_code=status.HTTP_201_CREATED)
def register(user_in: UserCreate, db: Session = Depends(get_db)):
    if db.query(User).filter(User.email == user_in.email).first():
        raise HTTPException(status_code=400, detail="Email already registered")
    
    db_user = User(
        first_name=user_in.first_name,
        last_name=user_in.last_name,
        patronymic=user_in.patronymic,
        email=user_in.email,
        hashed_password=get_password_hash(user_in.password)
    )
    db.add(db_user)
    db.commit()
    db.refresh(db_user)
    return db_user


@router.post("/login", response_model=Token)
def login(
    form_data: OAuth2PasswordRequestForm = Depends(),
    db: Session = Depends(get_db),
    redirect_url: Optional[str] = Query(None),
    state: Optional[str] = Query(None)
):
    """
    Вход в систему по email и паролю.
    
    Параметры формы:
    - username: email пользователя (OAuth2 требует поле username, но мы используем его как email)
    - password: пароль
    
    Query параметры (опционально):
    - redirect_url: URL для редиректа после успешного логина
    - state: состояние для OAuth2 flow
    
    Возвращает JWT токен доступа.
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
                status_code=400,
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


@router.post("/logout")
def logout(current_user: User = Depends(get_current_user)):
    """
    Выход из системы.
    
    В stateless JWT logout реализуется на клиенте (удаление токена).
    Сервер просто подтверждает успех.
    """
    return {"message": "Successfully logged out"}


@router.get("/me", response_model=UserOut)
def get_profile(current_user: User = Depends(get_current_user)):
    """
    Получение данных текущего пользователя.
    """
    return current_user


@router.put("/me", response_model=UserOut)
def update_profile(
    user_update: UserUpdate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Обновление данных профиля текущего пользователя.
    """
    for field, value in user_update.model_dump(exclude_unset=True).items():
        if field == "password":
            value = get_password_hash(value)
        setattr(current_user, field, value)
    
    db.commit()
    db.refresh(current_user)
    return current_user


@router.delete("/me", status_code=status.HTTP_204_NO_CONTENT)
def soft_delete_account(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Мягкое удаление аккаунта текущего пользователя.
    
    Пользователь помечается как неактивный (is_active=False),
    но данные остаются в базе. После этого пользователь не может войти в систему.
    """
    current_user.is_active = False
    db.commit()