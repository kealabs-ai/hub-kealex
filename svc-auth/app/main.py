from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from app.infrastructure.database.session import _init_db
from app.api.routes.auth_routes import router as auth_router
from app.api.routes.user_routes import router as user_router
from app.api.routes.billing_routes import router as billing_router

app = FastAPI(title="svc-auth")
app.add_middleware(CORSMiddleware, allow_origins=["*"], allow_methods=["*"], allow_headers=["*"])
app.include_router(auth_router)
app.include_router(user_router)
app.include_router(billing_router)

@app.on_event("startup")
def startup_event():
    _init_db()

@app.get("/health")
def health_simple():
    return {"status": "healthy", "service": "svc-auth"}

@app.get("/k1/lex/health")
def health():
    return {"status": "ok", "service": "svc-auth"}
