import os

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api.routes.file_routes import router as file_router
from app.api.routes.repository_routes import router as repository_router
from app.core.config import STORAGE_PATH
from app.infrastructure.database.models.repository_model import Base
from app.infrastructure.database.session import engine

os.makedirs(STORAGE_PATH, exist_ok=True)

app = FastAPI(title="svc-repositorios")
app.add_middleware(CORSMiddleware, allow_origins=["*"], allow_methods=["*"], allow_headers=["*"])
app.include_router(repository_router)
app.include_router(file_router)


@app.on_event("startup")
def startup_event():
    Base.metadata.create_all(engine)


@app.get("/health")
def health():
    return {"status": "ok", "service": "svc-repositorios"}
