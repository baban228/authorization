# FastAPI RBAC Authorization System

Современный бэкенд на FastAPI, реализующий систему аутентификации и разграничения прав доступа.

## Настройка и Конфигурация

Приложение управляется через переменные окружения. Мы используем Pydantic Settings для их валидации.
### 1. Файл .env
Создайте файл .env в корне проекта на основе .env.example.

Откройте .env и настройте параметры.

### 2. Зависимости
Введите команду в консоле: 
```
pip install -r requirements.txt
```
## Схема Базы Данных и Права Доступа (RBAC)
Система использует классическую модель RBAC (Role-Based Access Control).
### Сущности БД:
  Users: Пользователи системы. Имеют флаг is_active для мягкого удаления.
  
  Roles: Группы пользователей (например, admin, user, moderator).
  
  Permissions: Конкретные действия или ресурсы (например, read:users, delete:items).
  
  User_Roles: Связь Many-to-Many между пользователями и ролями.
  
  Role_Permissions: Связь Many-to-Many между ролями и разрешениями.
## Запуск проекта
### Способ 1: Docker Compose
  Идеально для быстрого старта и изоляции окружения.
  Убедитесь, что Docker Desktop запущен.
  Введите команду в консоле: 
  ```
  docker-compose up --build
  ```
  Приложение будет доступно по адресу: http://localhost:8000
  Данные SQLite сохраняются в Docker Volume authorization_sqlite_data, поэтому они не пропадут при перезапуске.
### Способ 2: Локальный запуск
  Активируйте виртуальное окружение:
  ```
  .venv\Scripts\activate
  ```
  Запустите сервер с автоперезагрузкой:
  ```
  uvicorn server.cmd.server.main:app --reload
  ```
  Откройте http://localhost:8000/docs для просмотра Swagger UI.
## Тестирование
  Проект включает набор интеграционных тестов, проверяющих основные сценарии ТЗ.
  Запустите тесты:
  ```
  pytest server/tests/ -v
  ```
  ### Что проверяют тесты:
  Регистрацию и вход в систему.
  
  Получение профиля с токеном и без него (401).
  
  Ошибку 403 для обычного пользователя при доступе к админ-панели.
  
  Мягкое удаление аккаунта и блокировку последующего входа.
  
  Доступ администратора к защищенным ресурсам.
## API Документация
FastAPI автоматически генерирует интерактивную документацию.

Swagger UI: http://localhost:8000/docs

ReDoc: http://localhost:8000/redoc
## Основные эндпоинты:
### Authentication (/auth)
POST /register — Регистрация нового пользователя.

POST /login — Вход (OAuth2 Password Flow). Возвращает JWT токен.

GET /me — Получить текущий профиль (требуется токен).

PUT /me — Обновить профиль (имя, пароль и т.д.).

DELETE /me — Мягко удалить аккаунт (блокировка входа).
### Admin (/admin) — Требуется право manage:roles
GET /roles — Список всех ролей.

POST /roles — Создать новую роль.

POST /permissions — Создать новое разрешение.

POST /assign-role — Назначить роль пользователю по ID.

POST /grant-permission — Выдать разрешение конкретной роли.
### Resources (/resources) — Демо защиты
GET /public — Доступно всем.

GET /protected — Требуется авторизация (любой активный юзер).

GET /admin-only — Требуется право manage:roles.
### Стек технологий
Core: Python 3.12, FastAPI, Uvicorn

DB: SQLAlchemy (ORM), SQLite (по умолчанию, легко заменить на PostgreSQL)

Validation: Pydantic V2

Security: JWT (python-jose), Passlib (bcrypt), OAuth2PasswordRequestForm

DevOps: Docker, Docker Compose, Pytest

## Архитектура проекта

Проект использует структуру, разделяющую код на логические модули для удобства поддержки и масштабирования:

```text
authorization/
├── server/
│   ├── cmd/
│   │   └── server/
│   │       └── main.py          # Точка входа в приложение
│   ├── internal/
│   │   ├── app/
│   │   │   ├── config.py        # Настройки приложения (Pydantic Settings)
│   │   │   ├── dependencies.py  # Зависимости FastAPI (Auth, Permissions)
│   │   │   └── security.py      # Логика JWT, хэширование паролей
│   │   ├── handlers/            # Обработчики запросов (Routes logic)
│   │   │   ├── auth.py          # Регистрация, логин, профиль
│   │   │   ├── admin.py         # Управление ролями и правами
│   │   │   └── resources.py     # Примеры защищенных ресурсов
│   │   ├── models/
│   │   │   ├── db_models.py     # Модели SQLAlchemy (Таблицы БД)
│   │   │   └── schemas.py       # Схемы Pydantic (Валидация данных)
│   │   ├── routers/             # Сборка API роутеров
│   │   └── storage/
│   │       ├── database.py      # Подключение к БД и сессии
│   │       └── seed.py          # Начальное заполнение БД (Админ, роли)
│   └── tests/                   # Юнит-тесты
├── Dockerfile                   # Инструкции для сборки образа
├── docker-compose.yml           # Оркестрация контейнеров
├── requirements.txt             # Зависимости Python
├── .env.example                 # Шаблон переменных окружения
└── README.md                    # Этот файл
