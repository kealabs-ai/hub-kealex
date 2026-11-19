from datetime import datetime

from fastapi import Depends, HTTPException
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from jose import JWTError, jwt
from sqlalchemy import text
from sqlalchemy.orm import Session

from app.core.config import ALGORITHM, KEALEX_SECRET_KEY
from app.infrastructure.database.session import get_db

bearer = HTTPBearer()


def verify_token(creds: HTTPAuthorizationCredentials = Depends(bearer), db: Session = Depends(get_db)):
    try:
        payload = jwt.decode(creds.credentials, KEALEX_SECRET_KEY, algorithms=[ALGORITHM])
    except JWTError as exc:
        raise HTTPException(401, "Token inválido") from exc
    if not payload.get("tenant_id") or not payload.get("sub"):
        raise HTTPException(401, "Token sem tenant ou usuário")
    if payload.get("role") == "admin":
        return payload

    row = db.execute(
        text("SELECT ativo, plano, trial_expires_at, subscription_status, subscription_expires_at FROM tenants WHERE id = :tenant_id"),
        {"tenant_id": payload["tenant_id"]},
    ).mappings().first()
    if row is None or not row["ativo"]:
        raise HTTPException(403, "Conta inativa. Regularize sua assinatura para continuar.")
    now = datetime.utcnow()
    if row["plano"] == "trial" and (not row["trial_expires_at"] or now < row["trial_expires_at"]):
        return payload
    if row["plano"] in {"starter", "professional", "enterprise"} and row["subscription_status"] == "active":
        if not row["subscription_expires_at"] or now < row["subscription_expires_at"]:
            return payload
    raise HTTPException(403, "Assinatura pendente ou vencida. Regularize o pagamento para continuar.")
