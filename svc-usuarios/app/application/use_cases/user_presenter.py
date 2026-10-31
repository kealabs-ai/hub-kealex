from sqlalchemy import text
from sqlalchemy.orm import Session
from app.infrastructure.database.models.user_model import Usuario, UsuarioChavePublica

def user_to_dict(u: Usuario, db: Session):
    escritorio_nome = None
    if u.escritorio_id:
        escritorio_nome = db.execute(
            text("SELECT nome FROM escritorios WHERE id = :eid AND tenant_id = :tid"),
            {"eid": u.escritorio_id, "tid": u.tenant_id}
        ).scalar_one_or_none()
    return {
        "id": u.id, "tenantId": u.tenant_id, "escritorioId": u.escritorio_id,
        "escritorioNome": escritorio_nome,
        "codigoEscritorio": u.codigo,
        "modalidade": "escritorio" if u.escritorio_id else "autonomo",
        "nome": u.nome, "email": u.email, "role": u.role, "ativo": u.ativo, "oab": getattr(u, "oab", None),
        "createdAt": u.created_at.isoformat(), "updatedAt": u.updated_at.isoformat()
    }

def public_key_to_dict(item: UsuarioChavePublica):
    return {
        "id": item.id,
        "userId": item.user_id,
        "orgao": item.orgao,
        "chavePublica": item.chave_publica,
        "createdAt": item.created_at.isoformat(),
        "updatedAt": item.updated_at.isoformat(),
    }
