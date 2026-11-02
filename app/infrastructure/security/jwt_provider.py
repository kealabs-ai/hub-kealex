from datetime import datetime, timedelta

from fastapi import Depends, HTTPException
from fastapi.security import HTTPAuthorizationCredentials
from jose import JWTError, jwt

from app.core.config import ALGORITHM, KEALEX_SECRET_KEY, TOKEN_EXPIRE_MINUTES
from app.infrastructure.database.models import Usuario
from app.infrastructure.database.session import bearer

def _make_token(user: Usuario) -> str:
    exp = datetime.utcnow() + timedelta(minutes=TOKEN_EXPIRE_MINUTES)
    return jwt.encode(
        {"sub": user.id, "role": user.role, "tenant_id": user.tenant_id, "exp": exp},
        KEALEX_SECRET_KEY, ALGORITHM
    )

def verify_token(creds: HTTPAuthorizationCredentials = Depends(bearer)):
    try:
        return jwt.decode(creds.credentials, KEALEX_SECRET_KEY, algorithms=[ALGORITHM])
    except JWTError:
        raise HTTPException(401, "Token inválido")


__all__ = ["_make_token", "verify_token"]
