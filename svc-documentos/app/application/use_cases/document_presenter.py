from app.infrastructure.database.models.document_model import Documento

def _to_dict(d: Documento):
    return {
        "id": d.id, "tenantId": d.tenant_id, "userId": d.user_id, "escritorioId": d.escritorio_id,
        "processoId": d.processo_id, "uploadadoPorId": d.uploadado_por_id, "nome": d.nome, "tipo": d.tipo,
        "status": d.status, "urlArquivo": d.url_arquivo, "tamanhoBytes": d.tamanho_bytes,
        "createdAt": d.created_at.isoformat(), "updatedAt": d.updated_at.isoformat()
    }

