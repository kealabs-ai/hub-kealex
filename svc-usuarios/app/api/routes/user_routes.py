from datetime import datetime
from typing import Optional
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import text
from sqlalchemy.orm import Session
from app.api.dependencies import admin_guard, base_guard, team_guard
from app.api.schemas.user_schema import UsuarioIn, UsuarioListIn, UsuarioGetIn, UsuarioUpdate, UsuarioDeleteIn, ModalidadeIn
from app.application.use_cases.office_capacity import ensure_escritorio_capacity
from app.application.use_cases.user_presenter import user_to_dict
from app.domain.entities.role import RoleEnum
from app.infrastructure.database.models.user_model import Usuario
from app.infrastructure.database.session import get_db
from app.infrastructure.security.bcrypt_hasher import hash_password

router = APIRouter()

@router.get("/v1/lex/usuarios")
def list_usuarios(db: Session = Depends(get_db), payload=Depends(team_guard)):
    tenant_id = payload.get("tenant_id") or payload.get("sub")
    q = db.query(Usuario).filter_by(tenant_id=tenant_id)
    if payload.get("role") == "escritorio":
        q = q.filter_by(escritorio_id=payload.get("escritorio_id"), role=RoleEnum.advogado)
    return [user_to_dict(u, db) for u in q.all()]


@router.post("/v1/lex/usuarios/list")
def list_usuarios_filtered(body: UsuarioListIn, db: Session = Depends(get_db), payload=Depends(team_guard)):
    tenant_id = payload.get("tenant_id") or payload.get("sub")
    q = db.query(Usuario).filter_by(tenant_id=tenant_id)
    if body.role:
        q = q.filter_by(role=body.role)
    if payload.get("role") == "escritorio":
        q = q.filter_by(escritorio_id=payload.get("escritorio_id"), role=RoleEnum.advogado)
    return [user_to_dict(u, db) for u in q.all()]


@router.post("/v1/lex/usuarios/get")
def get_usuario(body: UsuarioGetIn, db: Session = Depends(get_db), payload=Depends(team_guard)):
    tenant_id = payload.get("tenant_id") or payload.get("sub")
    u = db.query(Usuario).filter_by(id=body.id, tenant_id=tenant_id).first()
    if payload.get("role") == "escritorio" and (u is None or u.escritorio_id != payload.get("escritorio_id") or u.role != RoleEnum.advogado):
        raise HTTPException(404, "NÃ£o encontrado")
    if not u:
        raise HTTPException(404, "Não encontrado")
    return user_to_dict(u, db)


@router.post("/v1/lex/usuarios", status_code=201)
def create_usuario(body: UsuarioIn, db: Session = Depends(get_db), payload=Depends(team_guard)):
    tid = payload.get("tenant_id") or payload.get("sub")
    escritorio_id = body.escritorioId
    if payload.get("role") == "escritorio":
        escritorio_id = payload.get("escritorio_id")
        if body.role != RoleEnum.advogado:
            raise HTTPException(403, "O escritÃ³rio pode cadastrar apenas advogados associados")
    if body.role == RoleEnum.escritorio:
        raise HTTPException(403, "A conta de escritÃ³rio deve ser criada pelo administrador")
    if escritorio_id:
        ensure_escritorio_capacity(db, tid, escritorio_id)
        codigo_escritorio = db.execute(
            text("SELECT codigo FROM escritorios WHERE id = :eid AND tenant_id = :tid"),
            {"eid": escritorio_id, "tid": tid},
        ).scalar_one_or_none()
    else:
        codigo_escritorio = None
    if db.query(Usuario).filter_by(email=body.email, tenant_id=tid).first():
        raise HTTPException(409, "Email já cadastrado")
    u = Usuario(tenant_id=tid, escritorio_id=escritorio_id, codigo=codigo_escritorio, nome=body.nome, email=body.email,
                senha_hash=hash_password(body.senha), role=body.role)
    if hasattr(u, "oab"):
        u.oab = body.oab
    db.add(u); db.commit(); db.refresh(u)
    return user_to_dict(u, db)


@router.post("/v1/lex/usuarios/update")
def update_usuario(body: UsuarioUpdate, db: Session = Depends(get_db), payload=Depends(team_guard)):
    tenant_id = payload.get("tenant_id") or payload.get("sub")
    u = db.query(Usuario).filter_by(id=body.id, tenant_id=tenant_id).first()
    if payload.get("role") == "escritorio" and u and (u.escritorio_id != payload.get("escritorio_id") or u.role != RoleEnum.advogado):
        raise HTTPException(404, "UsuÃ¡rio nÃ£o encontrado")
    if payload.get("role") == "escritorio" and (body.role not in (None, RoleEnum.advogado) or body.escritorioId is not None or body.clearEscritorio):
        raise HTTPException(403, "O escritÃ³rio pode editar apenas seus advogados associados")
    if not u:
        raise HTTPException(404, "Não encontrado")
    if body.escritorioId and not db.execute(
        text("SELECT id FROM escritorios WHERE id = :eid AND tenant_id = :tid"),
        {"eid": body.escritorioId, "tid": tenant_id},
    ).first():
        raise HTTPException(404, "Escritório não encontrado")
    target_escritorio_id = body.escritorioId if body.escritorioId is not None else (None if body.clearEscritorio else u.escritorio_id)
    will_be_active = body.ativo if body.ativo is not None else u.ativo
    adding_active_member = bool(
        target_escritorio_id
        and will_be_active
        and (target_escritorio_id != u.escritorio_id or not u.ativo)
    )
    if adding_active_member:
        ensure_escritorio_capacity(db, tenant_id, target_escritorio_id, exclude_user_id=u.id)
    data = body.model_dump(exclude_none=True, exclude={"id", "clearEscritorio"})
    if "senha" in data:
        u.senha_hash = hash_password(data.pop("senha"))
    if "escritorioId" in data:
        u.escritorio_id = data.pop("escritorioId")
        u.codigo = db.execute(
            text("SELECT codigo FROM escritorios WHERE id = :eid"), {"eid": u.escritorio_id}
        ).scalar_one_or_none() if u.escritorio_id else None
    elif body.clearEscritorio:
        u.escritorio_id = None
        u.codigo = None
    for k, v in data.items():
        setattr(u, k, v)
    u.updated_at = datetime.utcnow()
    db.commit(); db.refresh(u)
    return user_to_dict(u, db)


@router.post("/v1/lex/usuarios/delete")
def delete_usuario(body: UsuarioDeleteIn, db: Session = Depends(get_db), payload=Depends(admin_guard)):
    tenant_id = payload.get("tenant_id") or payload.get("sub")
    u = db.query(Usuario).filter_by(id=body.id, tenant_id=tenant_id).first()
    if not u:
        raise HTTPException(404, "Não encontrado")
    db.delete(u); db.commit()
    return {"ok": True}


@router.post("/v1/lex/usuarios/modalidade")
def set_modalidade(body: ModalidadeIn, db: Session = Depends(get_db), payload=Depends(base_guard)):
    """Admin gerencia membros; advogado pode alterar apenas o próprio vínculo."""
    tenant_id = payload.get("tenant_id") or payload.get("sub")
    uid = body.usuarioId
    if payload.get("role") != "admin" and (payload.get("role") != "advogado" or uid != payload.get("sub")):
        raise HTTPException(403, "Você só pode alterar sua própria modalidade")
    u = db.query(Usuario).filter_by(id=uid, tenant_id=tenant_id).first()
    if not u:
        raise HTTPException(404, "Usuário não encontrado")
    if body.escritorioId and not db.execute(
        text("SELECT id FROM escritorios WHERE id = :eid AND tenant_id = :tid"),
        {"eid": body.escritorioId, "tid": tenant_id},
    ).first():
        raise HTTPException(404, "Escritório não encontrado")
    if body.escritorioId and body.escritorioId != u.escritorio_id and u.ativo:
        ensure_escritorio_capacity(db, tenant_id, body.escritorioId, exclude_user_id=u.id)
    u.escritorio_id = body.escritorioId
    u.codigo = db.execute(
        text("SELECT codigo FROM escritorios WHERE id = :eid"), {"eid": body.escritorioId}
    ).scalar_one_or_none() if body.escritorioId else None
    u.updated_at = datetime.utcnow()
    db.commit(); db.refresh(u)
    return user_to_dict(u, db)


@router.get("/v1/lex/usuarios/me")
def get_me(db: Session = Depends(get_db), payload=Depends(base_guard)):
    """Retorna dados do próprio usuário autenticado."""
    uid = payload.get("sub")
    tenant_id = payload.get("tenant_id")
    u = db.query(Usuario).filter_by(id=uid, tenant_id=tenant_id).first()
    if not u:
        raise HTTPException(404, "Não encontrado")
    return user_to_dict(u, db)
