import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from server.internal.storage.database import Base, get_db
from server.cmd.server.main import app


SQLALCHEMY_DATABASE_URL = "sqlite:///./test.db"
engine = create_engine(SQLALCHEMY_DATABASE_URL, connect_args={"check_same_thread": False})
TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

Base.metadata.create_all(bind=engine)

def override_get_db():
    try:
        db = TestingSessionLocal()
        yield db
    finally:
        db.close()

app.dependency_overrides[get_db] = override_get_db

client = TestClient(app)


def register_user(email: str, password: str, first_name="Test", last_name="User"):
    """Регистрирует пользователя и возвращает ответ"""
    response = client.post("/api/v1/auth/register", json={
        "email": email,
        "password": password,
        "first_name": first_name,
        "last_name": last_name
    })
    return response

def login_user(email: str, password: str):
    """Логинится и возвращает токен"""
    response = client.post("/api/v1/auth/login", data={
        "username": email,
        "password": password
    })
    assert response.status_code == 200, f"Login failed: {response.json()}"
    return response.json()["access_token"]

def get_headers(token: str):
    """Формирует заголовки для авторизованных запросов"""
    return {"Authorization": f"Bearer {token}"}


def test_01_register_and_login():
    """ТЗ: Регистрация и вход в систему"""
    resp_reg = register_user("user1@test.com", "password123")
    assert resp_reg.status_code == 201
    assert resp_reg.json()["email"] == "user1@test.com"

    token = login_user("user1@test.com", "password123")
    assert token is not None
    print(f"\n✅ User registered and logged in. Token: {token[:20]}...")

def test_02_access_profile_with_token():
    """ТЗ: Идентификация пользователя по токену"""
    token = login_user("user1@test.com", "password123")
    
    resp = client.get("/api/v1/auth/me", headers=get_headers(token))
    assert resp.status_code == 200
    assert resp.json()["email"] == "user1@test.com"
    print("✅ Profile accessed successfully with token.")

def test_03_access_profile_without_token():
    """ТЗ: Ошибка 401 при отсутствии токена"""
    resp = client.get("/api/v1/auth/me") 
    assert resp.status_code == 401
    print("✅ 401 Unauthorized received for missing token.")

def test_04_regular_user_forbidden_on_admin_routes():
    """ТЗ: Ошибка 403 для пользователя без прав на админ-ресурсы"""
    token = login_user("user1@test.com", "password123")

    resp = client.get("/api/v1/admin/roles", headers=get_headers(token))

    assert resp.status_code == 403
    print("✅ 403 Forbidden received for regular user on admin route.")

def test_05_soft_delete_and_login_block():
    """ТЗ: Мягкое удаление и блокировка входа"""
    token = login_user("user1@test.com", "password123")
    
    resp_delete = client.delete("/api/v1/auth/me", headers=get_headers(token))
    assert resp_delete.status_code == 204

    resp_login_again = client.post("/api/v1/auth/login", data={
        "username": "user1@test.com",
        "password": "password123"
    })
    
    assert resp_login_again.status_code == 401
    print("✅ Account soft-deleted. Login blocked with 401.")

def test_06_admin_access():
    """ТЗ: Администратор имеет доступ к управлению правами"""
    from server.internal.models.db_models import User, Role, UserRole, Permission, RolePermission
    from server.internal.app.security import get_password_hash
    
    db = TestingSessionLocal()

    db.query(UserRole).delete()
    db.query(RolePermission).delete()
    db.query(User).filter(User.email == "admin@test.com").delete()
    db.query(Role).filter(Role.name == "admin").delete()
    db.query(Permission).filter(Permission.name == "manage:roles").delete()
    db.commit()

    perm = Permission(name="manage:roles")
    db.add(perm)
    db.flush()
    
    role = Role(name="admin")
    db.add(role)
    db.flush()
    
    db.add(RolePermission(role_id=role.id, permission_id=perm.id))

    admin_user = User(
        email="admin@test.com",
        hashed_password=get_password_hash("adminpass"),
        first_name="Admin",
        last_name="Adminov",
        is_active=True
    )
    db.add(admin_user)
    db.flush()
    
    db.add(UserRole(user_id=admin_user.id, role_id=role.id))
    db.commit()
    db.close()

    token = login_user("admin@test.com", "adminpass")
    
    resp = client.get("/api/v1/admin/roles", headers=get_headers(token))
    assert resp.status_code == 200
    assert len(resp.json()) > 0
    print("✅ Admin successfully accessed protected resource.")

if __name__ == "__main__":
    pytest.main([__file__, "-v"])