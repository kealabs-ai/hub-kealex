from datetime import datetime, timedelta


def grant_subscription_period(tenant, payment_id: str | None, plan: str | None = None) -> bool:
    """Grant or renew access once for each confirmed payment."""
    if not payment_id or tenant.last_paid_payment_id == payment_id:
        return False

    now = datetime.utcnow()
    current_expiration = tenant.subscription_expires_at
    base = current_expiration if current_expiration and current_expiration > now else now
    cycle = (tenant.subscription_cycle or "MONTHLY").upper()
    period_days = 90 if cycle in ("QUARTERLY", "TRIMESTRAL") else 30

    tenant.subscription_expires_at = base + timedelta(days=period_days)
    tenant.last_paid_payment_id = payment_id
    tenant.subscription_status = "active"
    tenant.plano = plan or tenant.subscription_plan or tenant.plano
    tenant.ativo = True
    tenant.updated_at = now
    return True
