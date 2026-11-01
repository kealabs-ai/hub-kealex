import logging

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api.routes.cobrancas_routes import router as cobrancas_router
from app.infrastructure.database.models.cobranca_model import Base
from app.infrastructure.database.session import engine

logging.basicConfig(level=logging.DEBUG, format="%(asctime)s - %(name)s - %(levelname)s - %(message)s")
app = FastAPI(title="svc-cobrancas")
app.add_middleware(CORSMiddleware, allow_origins=["*"], allow_methods=["*"], allow_headers=["*"])
app.include_router(cobrancas_router)


@app.on_event("startup")
def startup_event():
    try:
        Base.metadata.create_all(engine)
    except Exception as exc:
        print(f"[ERRO] Database init falhou: {type(exc).__name__}: {exc}")
        import traceback
        traceback.print_exc()


@app.get("/health")
def health():
    return {"status": "healthy", "service": "svc-cobrancas"}
