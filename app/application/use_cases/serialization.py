from sqlalchemy.orm import Session

from app.infrastructure.database.models import (
    Activity, ActivityColumn, Audiencia, Cliente, Cobranca, Fase, Intimacao,
    Processo, UsuarioChavePublica, UserApiKey,
)

def _activity_column_json(column: ActivityColumn) -> dict:
    return {
        "id": column.id, "title": column.title, "color": column.color,
        "position": column.position, "createdAt": column.created_at.isoformat(),
        "updatedAt": column.updated_at.isoformat(),
    }

def _audiencia_to_dict(row: Audiencia) -> dict:
    return {
        "id": row.id,
        "tenantId": row.tenant_id,
        "userId": row.user_id,
        "processoId": row.processo_id or "",
        "processoTitulo": row.processo_titulo,
        "tipo": row.tipo,
        "dataHora": row.data_hora,
        "local": row.local,
        "juiz": row.juiz,
        "partes": row.partes,
        "observacoes": row.observacoes,
        "roteiro": row.roteiro,
        "status": row.status,
        "createdAt": row.created_at.isoformat(),
        "updatedAt": row.updated_at.isoformat(),
    }

def _enrich_processos(db: Session, processos: list[Processo]):
    ids = list({p.cliente_id for p in processos})
    clientes = {c.id: c for c in db.query(Cliente).filter(Cliente.id.in_(ids)).all()}
    return [_processo_to_dict(p, clientes.get(p.cliente_id), db) for p in processos]

def _processo_to_dict(p: Processo, cliente: Cliente = None, db: Session = None):
    fases = []
    if db and hasattr(p, 'id'):
        fases = db.query(Fase).filter_by(processo_id=p.id).order_by(Fase.ordem).all()
    return {
        "id": p.id, "tenantId": p.tenant_id, "userId": p.user_id, "escritorioId": p.escritorio_id,
        "numero": p.numero, "titulo": p.titulo, "descricao": p.descricao, "status": p.status,
        "advogadoId": p.advogado_id, "clienteId": p.cliente_id,
        "clienteNome": cliente.nome if cliente else None,
        "clienteEmail": cliente.email if cliente else None,
        "vara": p.vara, "tribunal": p.tribunal,
        "fases": [{"id": f.id, "label": f.label, "ordem": f.ordem, "status": f.status, "dataConclusao": f.data_conclusao.isoformat() if f.data_conclusao else None} for f in fases],
        "createdAt": p.created_at.isoformat(), "updatedAt": p.updated_at.isoformat()
    }

def _cobranca_to_dict(c: Cobranca) -> dict:
    fases_labels = ["Pendente", "Aguardando Pagamento", "Vencida", "Em Cobrança", "Pago"]
    return {
        "id": c.id, "tenantId": c.tenant_id, "processoId": c.processo_id, "clienteId": c.cliente_id,
        "valorCentavos": c.valor_centavos, "status": c.status, "faseAtual": c.fase_atual,
        "faseLabel": fases_labels[c.fase_atual] if c.fase_atual < len(fases_labels) else "Desconhecida",
        "dataVencimento": c.data_vencimento.isoformat() if c.data_vencimento else None,
        "dataPagamento": c.data_pagamento.isoformat() if c.data_pagamento else None,
        "motivoCancelamento": c.motivo_cancelamento,
        "createdAt": c.created_at.isoformat(), "updatedAt": c.updated_at.isoformat(),
    }

def _activity_json(activity: Activity) -> dict:
    return {
        "id": activity.id, "userId": activity.user_id, "title": activity.title,
        "description": activity.description, "status": activity.status, "priority": activity.priority,
        "dueDate": activity.due_date.isoformat() if activity.due_date else None,
        "createdAt": activity.created_at.isoformat(), "updatedAt": activity.updated_at.isoformat(),
    }

def _row(obj) -> dict:
    d = {c.name: getattr(obj, c.name) for c in obj.__table__.columns}
    if "updated_at" in d and d["updated_at"]:
        d["updated_at"] = d["updated_at"].isoformat()
    return d

def _user_api_key_json(row: UserApiKey) -> dict:
    secret = _decrypt_user_api_key(row.api_key_encrypted)
    return {"id": row.id, "provider": row.provider, "model": row.model, "api_key_masked": "•" * max(4, min(12, len(secret) - 4)) + secret[-4:], "is_active": row.is_active, "created_at": row.created_at, "updated_at": row.updated_at}

def _public_key_to_dict(row: UsuarioChavePublica) -> dict:
    return {
        "id": row.id,
        "userId": row.user_id,
        "orgao": row.orgao,
        "chavePublica": row.chave_publica,
        "createdAt": row.created_at.isoformat(),
        "updatedAt": row.updated_at.isoformat(),
    }

def _intimacao_to_dict(row: Intimacao) -> dict:
    return {
        "id": row.id,
        "processoId": row.processo_id,
        "processoNumero": row.processo_numero,
        "processoTitulo": row.processo_titulo,
        "diario": row.diario,
        "dataPublicacao": row.data_publicacao,
        "conteudo": row.conteudo,
        "resumoIA": row.resumo_ia,
        "prazoCalculado": row.prazo_calculado,
        "status": row.status,
        "createdAt": row.created_at.isoformat(),
        "updatedAt": row.updated_at.isoformat(),
    }


__all__ = [name for name in globals() if not name.startswith("__")]
