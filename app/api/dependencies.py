from fastapi import Depends, HTTPException

from app.infrastructure.security.jwt_provider import verify_token

def _require_admin(payload=Depends(verify_token)):
    if payload.get("role") != "admin":
        raise HTTPException(403, "Acesso negado")
    return payload


__all__ = ["_require_admin"]
