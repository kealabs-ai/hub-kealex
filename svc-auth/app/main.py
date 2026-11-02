from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from app.infrastructure.database.session import _init_db
from app.api.routes.auth_routes import router as auth_router
from app.api.routes.user_routes import router as user_router
from app.api.routes.billing_routes import router as billing_router
from app.infrastructure.messaging.access_events import publish_access_event
from prometheus_client import CONTENT_TYPE_LATEST, generate_latest
from fastapi.responses import Response

app = FastAPI(title="svc-auth")
app.add_middleware(CORSMiddleware, allow_origins=["*"], allow_methods=["*"], allow_headers=["*"])
app.include_router(auth_router)
app.include_router(user_router)
app.include_router(billing_router)

@app.on_event("startup")
def startup_event():
    _init_db()

@app.on_event("startup")
async def connect_access_queue():
    await publish_access_event.connect()

@app.on_event("shutdown")
async def close_access_queue():
    await publish_access_event.close()

@app.get("/health")
def health_simple():
    return {"status": "healthy", "service": "svc-auth"}

@app.get("/k1/lex/health")
def health():
    return {"status": "ok", "service": "svc-auth"}

@app.get("/metrics", include_in_schema=False)
def metrics():
    return Response(generate_latest(), media_type=CONTENT_TYPE_LATEST)
