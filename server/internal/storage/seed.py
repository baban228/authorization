from sqlalchemy.orm import Session
from server.internal.storage.database import SessionLocal
from server.internal.models.db_models import User, Role, Permission, UserRole, RolePermission
from server.internal.app.security import get_password_hash

def seed_db():
    db: Session = SessionLocal()
    try:
        if db.query(Role).first(): return 

        # Роли
        admin_role = Role(name="admin")
        user_role = Role(name="user")
        db.add_all([admin_role, user_role])
        db.flush()

        perms = [
            Permission(name="read:own_profile"),
            Permission(name="write:own_profile"),
            Permission(name="read:users"),
            Permission(name="write:users"),
            Permission(name="manage:roles")
        ]
        db.add_all(perms)
        db.flush()

        db.add_all([
            RolePermission(role_id=user_role.id, permission_id=1),
            RolePermission(role_id=user_role.id, permission_id=2),
            RolePermission(role_id=admin_role.id, permission_id=3),
            RolePermission(role_id=admin_role.id, permission_id=4),
            RolePermission(role_id=admin_role.id, permission_id=5),
        ])

        # Пользователи
        admin_user = User(
            first_name="Admin", last_name="Adminov", email="admin@example.com",
            hashed_password=get_password_hash("admin123")
        )
        test_user = User(
            first_name="Test", last_name="Userov", email="user@example.com",
            hashed_password=get_password_hash("user123")
        )
        db.add_all([admin_user, test_user])
        db.flush()

        db.add_all([
            UserRole(user_id=admin_user.id, role_id=admin_role.id),
            UserRole(user_id=test_user.id, role_id=user_role.id)
        ])

        db.commit()
        print("Database seeded successfully")
    finally:
        db.close()