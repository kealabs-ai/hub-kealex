from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from app.api.routes.agent_routes import router as agent_router
from app.api.routes.configuration_routes import router as configuration_router
from app.api.routes.drive_routes import router as drive_router
from app.infrastructure.database.models.configuration_model import Base
from app.infrastructure.database.session import engine
app = FastAPI(title="svc-configuracoes")
app.add_middleware(CORSMiddleware, allow_origins=["*"], allow_methods=["*"], allow_headers=["*"])
app.include_router(configuration_router)
app.include_router(agent_router)
app.include_router(drive_router)
@app.on_event("startup")
def startup_event():
    Base.metadata.create_all(engine)
@app.get("/health")
def health():
    return {"status": "ok", "service": "svc-configuracoes"}
