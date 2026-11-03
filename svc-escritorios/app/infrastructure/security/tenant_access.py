from datetime import datetime

from fastapi import HTTPException
from sqlalchemy import text
from sqlalchemy.orm import Session


def enforce_active_tenant(payload: dict, db: Session) -> dict:
    """Fail closed unless the signed tenant claim has an active entitlement."""
    if payload.get("role") == "admin":
        return payload

    tenant_id = payload.get("tenant_id")
    if not tenant_id:
        raise HTTPException(403, "Conta sem tenant associado")

    row = db.execute(
        text(
            "SELECT ativo, plano, trial_expires_at, subscription_status, "
            "subscription_expires_at FROM tenants WHERE id = :tenant_id"
        ),
        {"tenant_id": tenant_id},
    ).mappings().first()
    if row is None or not row["ativo"]:
        raise HTTPException(403, "Conta inativa. Regularize sua assinatura para continuar.")

    now = datetime.utcnow()
    if row["plano"] == "trial":
        if row["trial_expires_at"] and now >= row["trial_expires_at"]:
            raise HTTPException(403, "Trial expirado. Assine um plano para continuar.")
        return payload

    if row["plano"] in ("starter", "professional", "enterprise") and row["subscription_status"] == "active":
        if row["subscription_expires_at"] and now >= row["subscription_expires_at"]:
            raise HTTPException(403, "Sua assinatura expirou. Renove o plano para continuar.")
        return payload

    raise HTTPException(403, "Assinatura pendente ou vencida. Regularize o pagamento para continuar.")
