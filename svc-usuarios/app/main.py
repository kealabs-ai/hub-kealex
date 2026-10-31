from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from app.api.routes.user_routes import router as user_router
from app.api.routes.public_key_routes import router as public_key_router
from app.api.routes.datajud_routes import router as datajud_router
from app.infrastructure.database.models.user_model import Base
from app.infrastructure.database.session import engine

app = FastAPI(title="svc-usuarios")
app.add_middleware(CORSMiddleware, allow_origins=["*"], allow_methods=["*"], allow_headers=["*"])
app.include_router(user_router)
app.include_router(public_key_router)
app.include_router(datajud_router)

def initialize_database():
    Base.metadata.create_all(engine)

@app.on_event("startup")
def startup_event():
    initialize_database()

@app.get("/health")
def health():
    return {"status": "ok", "service": "svc-usuarios"}
