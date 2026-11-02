import os

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.legacy_context import *
from app.api.routes.activity_routes import router as activity_router
from app.api.routes.admin_config_routes import router as admin_config_router
from app.api.routes.agent_routes import router as agent_router
from app.api.routes.ai_routes import router as ai_router
from app.api.routes.auth_routes import router as auth_router
from app.api.routes.billing_routes import router as billing_router
from app.api.routes.process_routes import router as process_router
from app.api.routes.public_key_routes import router as public_key_router
from app.api.routes.resource_routes import router as resource_router
from app.api.routes.system_routes import router as system_router

app = FastAPI(title="HubKealex API")
cors_allowed_origins = [
    origin.strip()
    for origin in os.getenv("KEALEX_CORS_ALLOWED_ORIGINS", "").split(",")
    if origin.strip()
]
app.add_middleware(
    CORSMiddleware,
    allow_origins=cors_allowed_origins,
    allow_methods=["*"],
    allow_headers=["*"],
    allow_credentials=True,
)
def startup_event():
    _init_db()


app.add_event_handler("startup", startup_event)
for router in (
    auth_router,
    activity_router,
    system_router,
    process_router,
    resource_router,
    public_key_router,
    ai_router,
    agent_router,
    billing_router,
    admin_config_router,
):
    app.include_router(router)
