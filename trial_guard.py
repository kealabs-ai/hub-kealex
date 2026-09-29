"""
trial_guard.py â€” dependÃªncia FastAPI reutilizÃ¡vel para controle de trial.

Uso em qualquer svc-*:
    from trial_guard import require_active_trial

    @app.get("/minha-rota")
    def minha_rota(payload=Depends(require_active_trial)):
        ...
"""
import os
from datetime import datetime
from fastapi import HTTPException, Depends
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from jose import jwt, JWTError
from sqlalchemy import create_engine, Column, String, Boolean, DateTime
from sqlalchemy.orm import DeclarativeBase, Session, sessionmaker

KEALEX_SECRET_KEY = os.getenv("KEALEX_SECRET_KEY") or os.getenv("KEALEX_JWT_SECRET")
if not KEALEX_SECRET_KEY:
    raise RuntimeError("KEALEX_SECRET_KEY ou KEALEX_JWT_SECRET precisa estar configurada no ambiente")
ALGORITHM = "HS256"

KEALEX_DATABASE_URL = os.getenv("KEALEX_DATABASE_URL")
if not KEALEX_DATABASE_URL:
    raise RuntimeError("KEALEX_DATABASE_URL precisa estar configurada no ambiente")

_engine = create_engine(
    KEALEX_DATABASE_URL, pool_pre_ping=True, pool_recycle=280, pool_size=3, max_overflow=5)
_SessionLocal = sessionmaker(bind=_engine, autocommit=False, autoflush=False)
_bearer       = HTTPBearer()

class _Base(DeclarativeBase): pass

class _Tenant(_Base):
    __tablename__ = "tenants"
    id = Column(String(36), primary_key=True)
    plano = Column(String(20), default="trial")
    trial_expires_at = Column(DateTime, nullable=True)
    subscription_status = Column(String(20), nullable=False, default="trialing")
    ativo = Column(Boolean, default=True)

def _get_db():
    db = _SessionLocal()
    try:
        yield db
    finally:
        db.close()

def verify_token(creds: HTTPAuthorizationCredentials = Depends(_bearer)) -> dict:
    try:
        return jwt.decode(creds.credentials, KEALEX_SECRET_KEY, algorithms=[ALGORITHM])
    except JWTError:
        raise HTTPException(401, "Token invÃ¡lido")

def require_active_trial(
    payload: dict = Depends(verify_token),
    db: Session = Depends(_get_db),
) -> dict:
    role = payload.get("role", "")
    tenant_id = payload.get("tenant_id")
    if role == "admin":
        return payload
    if not tenant_id:
        raise HTTPException(403, "Conta sem tenant associado")

    tenant = db.query(_Tenant).filter_by(id=tenant_id).first()
    if tenant is None or not tenant.ativo:
        raise HTTPException(403, "Conta inativa. Regularize sua assinatura para continuar.")
    if tenant.plano == "trial":
        if tenant.trial_expires_at and datetime.utcnow() > tenant.trial_expires_at:
            raise HTTPException(403, "Trial expirado. Assine um plano para continuar.")
        return payload
    if tenant.plano in ("starter", "professional", "enterprise") and tenant.subscription_status == "active":
        return payload
    raise HTTPException(403, "Assinatura pendente ou vencida. Regularize o pagamento para continuar.")
