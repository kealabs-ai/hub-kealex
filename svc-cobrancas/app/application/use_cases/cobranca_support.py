from datetime import datetime, timezone

from app.infrastructure.database.models.cobranca_model import Cobranca


def now_utc():
    return datetime.now(timezone.utc).replace(tzinfo=None)


def build_asaas_payload(body, cobranca):
    payload = {
        "billingType": body.billingType,
        "customer": body.customer.strip(),
        "value": round(cobranca.valor_centavos / 100, 2),
        "dueDate": cobranca.data_vencimento.date().isoformat()
        if cobranca.data_vencimento
        else now_utc().date().isoformat(),
        "description": body.description or f"Cobranca {cobranca.id}",
        "externalReference": cobranca.id,
    }
    if body.billingType == "CREDIT_CARD":
        if body.creditCardToken:
            payload["creditCardToken"] = body.creditCardToken
        else:
            payload["creditCard"] = body.creditCard.model_dump()
            payload["creditCardHolderInfo"] = body.creditCardHolderInfo.model_dump(exclude_none=True)
    return payload


def serialize_charge(charge: Cobranca):
    phases = ["Pendente", "Aguardando Pagamento", "Vencida", "Em Cobranca", "Pago"]
    return {
        "id": charge.id,
        "tenantId": charge.tenant_id,
        "processoId": charge.processo_id,
        "clienteId": charge.cliente_id,
        "valorCentavos": charge.valor_centavos,
        "status": charge.status,
        "faseAtual": charge.fase_atual,
        "faseLabel": phases[charge.fase_atual] if charge.fase_atual < len(phases) else "Desconhecida",
        "dataVencimento": charge.data_vencimento.isoformat() if charge.data_vencimento else None,
        "dataPagamento": charge.data_pagamento.isoformat() if charge.data_pagamento else None,
        "motivoCancelamento": charge.motivo_cancelamento,
        "createdAt": charge.created_at.isoformat(),
        "updatedAt": charge.updated_at.isoformat(),
    }


def get_next_actions(charge: Cobranca):
    if charge.status in ("pago", "cancelado"):
        return []
    return [
        {"acao": "proxima_fase", "label": "Proxima Fase", "descricao": "Avancar para a proxima fase de cobranca"},
        {"acao": "marcar_pago", "label": "Marcar como Pago", "descricao": "Registrar pagamento recebido"},
        {"acao": "cancelar", "label": "Cancelar", "descricao": "Cancelar esta cobranca"},
    ]
