"""
trial_guard.py — dependência FastAPI reutilizável para controle de trial.

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

SECRET_KEY = os.getenv("SECRET_KEY", "changeme-secret-key")
ALGORITHM  = "HS256"

def _get_database_url(default: str) -> str:
    raw = os.getenv("DATABASE_URL")
    if raw is None or raw.strip().lower() in ("", "null", "none"):
        return default
    return raw.strip()

DATABASE_URL = _get_database_url(
    "mysql+pymysql://u549746795_kealex:Sally2026%40%21%40@srv1078.hstgr.io:3306/u549746795_kealex"
)

_engine       = create_engine(DATABASE_URL, pool_pre_ping=True, pool_recycle=280, pool_size=3, max_overflow=5)
_SessionLocal = sessionmaker(bind=_engine, autocommit=False, autoflush=False)
_bearer       = HTTPBearer()

class _Base(DeclarativeBase): pass

class _Tenant(_Base):
    __tablename__ = "tenants"
    id               = Column(String(36), primary_key=True)
    plano            = Column(String(20), default="trial")
    trial_expires_at = Column(DateTime,   nullable=True)
    ativo            = Column(Boolean,    default=True)

def _get_db():
    db = _SessionLocal()
    try:
        yield db
    finally:
        db.close()

def verify_token(creds: HTTPAuthorizationCredentials = Depends(_bearer)) -> dict:
    try:
        return jwt.decode(creds.credentials, SECRET_KEY, algorithms=[ALGORITHM])
    except JWTError:
        raise HTTPException(401, "Token inválido")

def require_active_trial(
    payload: dict = Depends(verify_token),
    db: Session = Depends(_get_db),
) -> dict:
    """
    Verifica token + trial ativo.
    - Admin nunca é bloqueado.
    - Planos pagos nunca são bloqueados.
    - Trial expirado → 403.
    """
    role      = payload.get("role", "")
    tenant_id = payload.get("tenant_id")

    if role == "admin" or not tenant_id:
        return payload

    tenant = db.query(_Tenant).filter_by(id=tenant_id).first()
    if tenant is None:
        return payload

    if tenant.plano != "trial":
        return payload

    if tenant.trial_expires_at and datetime.utcnow() > tenant.trial_expires_at:
        raise HTTPException(403, "Trial expirado. Assine um plano para continuar.")

    return payload
