from fastapi import APIRouter, Depends, Header, HTTPException
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from app.application.use_cases.kea_credits import CREDIT_PACKAGES, create_recharge, recharge_status, wallet_snapshot
from app.infrastructure.database.session import get_db
from app.infrastructure.security.jwt_provider import verify_token


router = APIRouter(prefix="/k1/lex/kea-store", tags=["kea-credits"])
ALLOWED_ROLES = {"admin", "advogado", "juridico", "escritorio"}


class RechargeIn(BaseModel):
    packageId: str = Field(min_length=1, max_length=40)


def _identity(payload: dict) -> tuple[str, str]:
    if payload.get("role") not in ALLOWED_ROLES:
        raise HTTPException(403, "Acesso não permitido")
    tenant_id, user_id = payload.get("tenant_id"), payload.get("sub")
    if not tenant_id or not user_id:
        raise HTTPException(403, "Conta sem organização associada")
    return str(tenant_id), str(user_id)


@router.get("/carteira")
def get_wallet(payload=Depends(verify_token), db: Session = Depends(get_db)):
    tenant_id, _ = _identity(payload)
    return wallet_snapshot(db, tenant_id)


@router.get("/pacotes")
def list_credit_packages(payload=Depends(verify_token)):
    _identity(payload)
    return [{"id": package_id, "nome": package["name"], "credits": package["credits"], "valorCentavos": package["price_cents"]} for package_id, package in CREDIT_PACKAGES.items()]


@router.post("/recargas", status_code=201)
def post_recharge(
    body: RechargeIn,
    idempotency_key: str | None = Header(default=None, alias="Idempotency-Key"),
    payload=Depends(verify_token),
    db: Session = Depends(get_db),
):
    tenant_id, user_id = _identity(payload)
    if not idempotency_key:
        raise HTTPException(422, "Informe Idempotency-Key para criar a recarga")
    return create_recharge(db, tenant_id, user_id, body.packageId, idempotency_key)


@router.get("/recargas/{recharge_id}")
def get_recharge(recharge_id: str, payload=Depends(verify_token), db: Session = Depends(get_db)):
    tenant_id, _ = _identity(payload)
    return recharge_status(db, tenant_id, recharge_id)
