from datetime import datetime
from app.domain.exceptions import TenantAccessDenied


def check_tenant_access(tenant, role: str) -> None:
    if role == "admin":
        return
    if tenant is None:
        raise TenantAccessDenied("Conta sem assinatura válida. Regularize o pagamento para continuar.")
    if not tenant.ativo:
        raise TenantAccessDenied("Conta inativa. Regularize sua assinatura para continuar.")
    if tenant.plano == "trial":
        if tenant.trial_expires_at and datetime.utcnow() >= tenant.trial_expires_at:
            raise TenantAccessDenied("Trial expirado. Assine um plano para continuar.")
        return
    if tenant.plano in ("starter", "professional", "enterprise") and tenant.subscription_status == "active":
        if tenant.subscription_expires_at and datetime.utcnow() >= tenant.subscription_expires_at:
            raise TenantAccessDenied("Sua assinatura expirou. Renove o plano para continuar.")
        return
    raise TenantAccessDenied("Assinatura pendente ou vencida. Regularize o pagamento para continuar.")
