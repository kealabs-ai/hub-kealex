from datetime import datetime, timedelta

from fastapi import Depends, HTTPException
from fastapi.security import HTTPAuthorizationCredentials
from jose import JWTError, jwt
from sqlalchemy.orm import Session

from app.core.config import ALGORITHM, KEALEX_SECRET_KEY, TOKEN_EXPIRE_MINUTES
from app.infrastructure.database.models import Usuario
from app.infrastructure.database.session import bearer, get_db
from app.infrastructure.security.tenant_access import enforce_active_tenant

def _make_token(user: Usuario) -> str:
    exp = datetime.utcnow() + timedelta(minutes=TOKEN_EXPIRE_MINUTES)
    return jwt.encode(
        {"sub": user.id, "role": user.role, "tenant_id": user.tenant_id, "exp": exp},
        KEALEX_SECRET_KEY, ALGORITHM
    )

def verify_identity_token(creds: HTTPAuthorizationCredentials = Depends(bearer)):
    try:
        payload = jwt.decode(creds.credentials, KEALEX_SECRET_KEY, algorithms=[ALGORITHM])
        if not payload.get("tenant_id") or not payload.get("sub"):
            raise HTTPException(401, "Token sem tenant ou usu�rio")
        return payload
    except JWTError:
        raise HTTPException(401, "Token inválido")


def verify_token(payload=Depends(verify_identity_token), db: Session = Depends(get_db)):
    return enforce_active_tenant(payload, db)


__all__ = ["_make_token", "verify_identity_token", "verify_token"]
