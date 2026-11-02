import logging
import os

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api.routes.debug_routes import router as debug_router
from app.api.routes.phase_routes import router as phase_router
from app.api.routes.process_routes import router as process_router
from app.infrastructure.database.models.processo_model import Base
from app.infrastructure.database.session import engine

logging.basicConfig(
    level=logging.DEBUG if os.getenv("KEALEX_DEBUG", "false").lower() == "true" else logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
)
app = FastAPI(title="svc-processos")
app.add_middleware(CORSMiddleware, allow_origins=["*"], allow_methods=["*"], allow_headers=["*"])
app.include_router(process_router)
app.include_router(phase_router)
app.include_router(debug_router)


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
    return {"status": "healthy", "service": "svc-processos"}
