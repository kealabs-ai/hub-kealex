import traceback
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from app.api.routes.clientes_routes import router as clientes_router
from app.infrastructure.database.models.client_model import Base
from app.infrastructure.database.session import engine

app = FastAPI(title="svc-clientes")
app.add_middleware(CORSMiddleware, allow_origins=["*"], allow_methods=["*"], allow_headers=["*"])
app.include_router(clientes_router)

def initialize_database():
    try:
        Base.metadata.create_all(engine)
    except Exception as exc:
        print(f"[ERRO] Database init falhou: {type(exc).__name__}: {str(exc)}")
        traceback.print_exc()

@app.on_event("startup")
def startup_event():
    initialize_database()

@app.get("/health")
def health():
    return {"status": "ok", "service": "svc-clientes"}
