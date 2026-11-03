from fastapi import Depends, HTTPException
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from jose import JWTError, jwt
from sqlalchemy.orm import Session
from app.infrastructure.database.session import get_db
from app.infrastructure.security.tenant_access import enforce_active_tenant

from app.core.config import ALGORITHM, KEALEX_SECRET_KEY

bearer = HTTPBearer()

def verify_token(creds: HTTPAuthorizationCredentials = Depends(bearer), db: Session = Depends(get_db)):
    try:
        payload = jwt.decode(creds.credentials, KEALEX_SECRET_KEY, algorithms=[ALGORITHM])
        if not payload.get("tenant_id") or not payload.get("sub"):
            raise HTTPException(401, "Token sem tenant ou usu�rio")
        return enforce_active_tenant(payload, db)
    except JWTError:
        raise HTTPException(401, "Token inv?lido")
