from datetime import datetime, timedelta
from fastapi import Depends, HTTPException
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from jose import jwt, JWTError
from app.core.config import ALGORITHM, KEALEX_SECRET_KEY, TOKEN_EXPIRE_MINUTES
from app.infrastructure.database.models.auth_models import Usuario

bearer = HTTPBearer()

def create_access_token(user: Usuario) -> str:
    expiration = datetime.utcnow() + timedelta(minutes=TOKEN_EXPIRE_MINUTES)
    return jwt.encode(
        {"sub": user.id, "role": user.role, "tenant_id": user.tenant_id, "escritorio_id": user.escritorio_id, "exp": expiration},
        KEALEX_SECRET_KEY,
        ALGORITHM,
    )

def verify_token(creds: HTTPAuthorizationCredentials = Depends(bearer)):
    try:
        return jwt.decode(creds.credentials, KEALEX_SECRET_KEY, algorithms=[ALGORITHM])
    except JWTError:
        raise HTTPException(401, "Token inválido")