from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from server.internal.routers import api_router
from server.internal.storage.database import engine, Base
from server.internal.storage.seed import seed_db

app = FastAPI(title="RBAC FastAPI App", version="1.0.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

@app.on_event("startup")
def on_startup():
    Base.metadata.create_all(bind=engine)
    seed_db()

app.include_router(api_router, prefix="/api/v1")