from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api.routes.document_routes import router as document_router
from app.api.routes.document_analysis_routes import router as document_analysis_router
from app.infrastructure.database.models.document_model import Base
from app.infrastructure.database.models import analysis_model as _analysis_models
from app.infrastructure.database.session import engine

app = FastAPI(title="svc-documentos")
app.add_middleware(CORSMiddleware, allow_origins=["*"], allow_methods=["*"], allow_headers=["*"])
app.include_router(document_router)
app.include_router(document_analysis_router)


@app.on_event("startup")
def startup_event():
    Base.metadata.create_all(engine)


@app.get("/health")
def health():
    return {"status": "ok", "service": "svc-documentos"}
