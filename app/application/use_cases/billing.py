import os
import hmac as _hmac

from app.core.config import KEALEX_ASAAS_API_KEY, KEALEX_ASAAS_WEBHOOK_TOKEN, ASAAS_BASE


def _verify_webhook_token(token: str | None) -> bool:
    """Valida o token do webhook usando comparação segura contra timing attacks."""
    if not KEALEX_ASAAS_WEBHOOK_TOKEN or not token:
        return False
    return _hmac.compare_digest(
        token.encode("utf-8"),
        KEALEX_ASAAS_WEBHOOK_TOKEN.encode("utf-8"),
    )

PLANOS = {
    "starter":      {"value": 197.00, "description": "Plano Starter"},
    "professional": {"value": 397.00, "description": "Plano Professional"},
}

def _calcular_valor(valor_mensal: float, periodicidade: str) -> tuple[float, int]:
    """Retorna (valor_total, installmentCount). Trimestral = 3x com 5% de desconto."""
    if periodicidade == "trimestral":
        return round(valor_mensal * 3 * 0.95, 2), 3
    return valor_mensal, 1

def _digits(value: str | None) -> str | None:
    if value is None: return None
    return "".join(c for c in value if c.isdigit())

__all__ = ["_verify_webhook_token", "_calcular_valor", "_digits", "PLANOS"]
