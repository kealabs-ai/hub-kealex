from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from app.api.routes.prazo_routes import router as prazo_router
from app.infrastructure.database.models.prazo_model import Base
from app.infrastructure.database.session import engine

app = FastAPI(title="svc-prazos")
app.add_middleware(CORSMiddleware, allow_origins=["*"], allow_methods=["*"], allow_headers=["*"])
app.include_router(prazo_router)


@app.on_event("startup")
def startup_event():
    Base.metadata.create_all(engine)


@app.get("/health")
def health():
    return {"status": "ok", "service": "svc-prazos"}
