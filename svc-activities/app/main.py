from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from app.api.routes.activity_routes import router as activity_router
from app.core.config import CORS_ALLOWED_ORIGINS
from app.core.middleware import ActivityConsoleLogMiddleware
from app.infrastructure.database.models.activity_model import Base
from app.infrastructure.database.session import engine

app = FastAPI(title="svc-activities")
app.add_middleware(CORSMiddleware, allow_origins=CORS_ALLOWED_ORIGINS, allow_methods=["GET", "POST", "OPTIONS"], allow_headers=["*"], allow_credentials=True)
app.add_middleware(ActivityConsoleLogMiddleware)
app.include_router(activity_router)


def initialize_database():
    try:
        Base.metadata.create_all(engine)
    except Exception as exc:
        print(f"[ERRO] Database init falhou: {type(exc).__name__}: {exc}")


@app.on_event("startup")
def startup_event():
    initialize_database()


@app.get("/health")
def health():
    return {"status": "ok", "service": "svc-activities"}
