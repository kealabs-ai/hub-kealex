from app.infrastructure.database.models.prazo_model import Prazo

def _to_dict(p: Prazo):
    return {
        "id": p.id, "tenantId": p.tenant_id, "userId": p.user_id, "escritorioId": p.escritorio_id,
        "processoId": p.processo_id, "advogadoId": p.advogado_id, "titulo": p.titulo, "descricao": p.descricao,
        "dataVencimento": p.data_vencimento, "status": p.status,
        "createdAt": p.created_at.isoformat(), "updatedAt": p.updated_at.isoformat()
    }

