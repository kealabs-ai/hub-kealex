from fastapi import Depends, HTTPException
from app.infrastructure.security.jwt_provider import verify_token

base_guard = verify_token

def require_admin_or_advogado(payload=Depends(verify_token)):
    if payload.get("role") not in ("admin", "advogado"):
        raise HTTPException(403, "Acesso negado")
    return payload

def client_access_guard(payload=Depends(base_guard)):
    if payload.get("role") not in ("admin", "advogado"):
        raise HTTPException(403, "Acesso negado")
    return payload
