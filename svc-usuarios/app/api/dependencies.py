from fastapi import Depends, HTTPException
from app.infrastructure.security.jwt_provider import verify_token

base_guard = verify_token

def admin_guard(payload=Depends(base_guard)):
    if payload.get("role") != "admin":
        raise HTTPException(403, "Acesso negado")
    return payload

def team_guard(payload=Depends(base_guard)):
    if payload.get("role") not in ("admin", "escritorio"):
        raise HTTPException(403, "Acesso negado")
    if payload.get("role") == "escritorio" and not payload.get("escritorio_id"):
        raise HTTPException(403, "Conta de escrit\u00f3rio sem v\u00ednculo configurado")
    return payload
