from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api.routes.fiscalapi_routes import router as fiscalapi_router
from app.api.routes.escavador_routes import router as escavador_router

app = FastAPI(title="svc-integracoes")
app.add_middleware(CORSMiddleware, allow_origins=["*"], allow_methods=["*"], allow_headers=["*"])
app.include_router(fiscalapi_router)
app.include_router(escavador_router)


@app.get("/health")
def health():
    return {"status": "ok", "service": "svc-integracoes"}
