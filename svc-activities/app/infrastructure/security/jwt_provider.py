from fastapi import Depends, HTTPException
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from jose import JWTError, jwt
from app.core.config import SECRET_KEY

bearer = HTTPBearer()


def verify_token(creds: HTTPAuthorizationCredentials = Depends(bearer)):
    try:
        payload = jwt.decode(creds.credentials, SECRET_KEY, algorithms=["HS256"])
        if not payload.get("tenant_id") or not payload.get("sub"):
            raise HTTPException(401, "Token sem tenant ou usu�rio")
        return payload
    except JWTError:
        raise HTTPException(401, "Token inv?lido")
