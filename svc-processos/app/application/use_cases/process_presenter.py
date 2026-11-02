from sqlalchemy.orm import Session
from app.infrastructure.database.models.processo_model import Cliente, Processo

def _to_dict(p: Processo, cliente: Cliente = None):
    fases = sorted(p.fases, key=lambda f: f.ordem) if p.fases else []
    return {
        "id": p.id, "tenantId": p.tenant_id, "userId": p.user_id, "escritorioId": p.escritorio_id,
        "numero": p.numero, "titulo": p.titulo, "descricao": p.descricao, "status": p.status,
        "advogadoId": p.advogado_id, "clienteId": p.cliente_id,
        "clienteNome": cliente.nome if cliente else None,
        "clienteEmail": cliente.email if cliente else None,
        "vara": p.vara, "tribunal": p.tribunal,
        "faseAtual": p.fase_atual,
        "fases": [
            {"id": f.id, "label": f.label, "status": f.status, "data": f.data_conclusao.isoformat() if f.data_conclusao else None}
            for f in fases
        ],
        "createdAt": p.created_at.isoformat(), "updatedAt": p.updated_at.isoformat()
    }

def _enrich(db: Session, processos: list[Processo]):
    ids = list({p.cliente_id for p in processos})
    clientes = {c.id: c for c in db.query(Cliente).filter(Cliente.id.in_(ids)).all()}
    return [_to_dict(p, clientes.get(p.cliente_id)) for p in processos]

