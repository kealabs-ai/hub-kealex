import sys

from fastapi import Depends, HTTPException
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from jose import JWTError, jwt

from app.core.config import ALGORITHM, SECRET_KEY

sys.path.insert(0, "/app")
try:
    from trial_guard import require_active_trial
except ImportError:
    require_active_trial = None

bearer = HTTPBearer()


def verify_token(creds: HTTPAuthorizationCredentials = Depends(bearer)):
    try:
        return jwt.decode(creds.credentials, SECRET_KEY, algorithms=[ALGORITHM])
    except JWTError:
        raise HTTPException(401, "Token invalido")


auth_guard = require_active_trial if require_active_trial else verify_token
