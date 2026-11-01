from app.infrastructure.database.models.honorario_model import Honorario

def _to_dict(h: Honorario):
    return {
        "id": h.id, "tenantId": h.tenant_id, "userId": h.user_id, "escritorioId": h.escritorio_id,
        "processoId": h.processo_id, "clienteId": h.cliente_id, "advogadoId": h.advogado_id, "descricao": h.descricao,
        "valorCentavos": h.valor_centavos, "dataVencimento": h.data_vencimento,
        "dataPagamento": h.data_pagamento, "status": h.status,
        "createdAt": h.created_at.isoformat(), "updatedAt": h.updated_at.isoformat()
    }

