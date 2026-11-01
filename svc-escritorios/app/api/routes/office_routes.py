import bcrypt
import secrets
import uuid
from datetime import datetime
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import text
from sqlalchemy.orm import Session
from app.api.dependencies import require_admin, verify_token
from app.api.schemas.office_schema import EscritorioIn, EscritorioGetIn, CriarAcessoIn, EscritorioUpdate, EscritorioDeleteIn, MembroIn, AssociarCodigoIn
from app.application.use_cases.office_presenter import _to_dict
from app.application.use_cases.office_usage import _usage_for_escritorio
from app.infrastructure.database.models.office_model import Escritorio
from app.infrastructure.database.session import get_db
router = APIRouter()

@router.get("/v1/lex/escritorios")
def list_escritorios(db: Session = Depends(get_db), payload=Depends(verify_token)):
    tenant_id = payload.get("tenant_id") or payload.get("sub")
    query = db.query(Escritorio).filter_by(tenant_id=tenant_id)
    if payload.get("role") == "escritorio":
        query = query.filter_by(id=payload.get("escritorio_id"))
    escritorios = query.all()
    result = []
    for escritorio in escritorios:
        usuarios_ativos, advogados_ativos = _usage_for_escritorio(db, escritorio.id)
        access = db.execute(text("SELECT id FROM usuarios WHERE escritorio_id = :eid AND tenant_id = :tid AND role = 'escritorio' LIMIT 1"), {"eid": escritorio.id, "tid": tenant_id}).first()
        result.append(_to_dict(escritorio, usuarios_ativos, advogados_ativos, bool(access)))
    return result

@router.post("/v1/lex/escritorios/get")
def get_escritorio(body: EscritorioGetIn, db: Session = Depends(get_db), payload=Depends(verify_token)):
    tenant_id = payload.get("tenant_id") or payload.get("sub")
    role = payload.get("role")
    if role == "advogado":
        membership = db.execute(
            text("SELECT escritorio_id FROM usuarios WHERE id = :uid AND tenant_id = :tid AND role = 'advogado'"),
            {"uid": payload.get("sub"), "tid": tenant_id},
        ).mappings().first()
        if not membership or membership["escritorio_id"] != body.id:
            raise HTTPException(404, "Escritorio associado nao encontrado")
        query = db.query(Escritorio).filter_by(id=body.id)
    else:
        query = db.query(Escritorio).filter_by(id=body.id, tenant_id=tenant_id)
        if role == "escritorio":
            query = query.filter_by(id=payload.get("escritorio_id"))
    e = query.first()
    if not e:
        raise HTTPException(404, "Não encontrado")
    usuarios_ativos, advogados_ativos = _usage_for_escritorio(db, e.id)
    access = db.execute(text("SELECT id FROM usuarios WHERE escritorio_id = :eid AND tenant_id = :tid AND role = 'escritorio' LIMIT 1"), {"eid": e.id, "tid": tenant_id}).first()
    return _to_dict(e, usuarios_ativos, advogados_ativos, bool(access))

@router.post("/v1/lex/escritorios/criar-acesso", status_code=201)
def create_escritorio_access(body: CriarAcessoIn, db: Session = Depends(get_db), payload=Depends(require_admin)):
    tenant_id = payload.get("tenant_id") or payload.get("sub")
    if len(body.senhaInicial) < 6:
        raise HTTPException(400, "A senha inicial precisa ter pelo menos 6 caracteres")
    office = db.query(Escritorio).filter_by(id=body.escritorioId, tenant_id=tenant_id).first()
    if not office:
        raise HTTPException(404, "Escritório não encontrado")
    if db.execute(text("SELECT id FROM usuarios WHERE escritorio_id = :eid AND tenant_id = :tid AND role = 'escritorio'"), {"eid": office.id, "tid": tenant_id}).first():
        raise HTTPException(409, "Este escritório já possui credenciais de acesso")
    if db.execute(text("SELECT id FROM usuarios WHERE email = :email"), {"email": body.emailAcesso}).first():
        raise HTTPException(409, "E-mail já cadastrado")
    db.execute(text("""
        INSERT INTO usuarios (id, tenant_id, escritorio_id, codigo, nome, email, senha_hash, role, ativo, created_at, updated_at)
        VALUES (:id, :tenant_id, :escritorio_id, :codigo, :nome, :email, :senha_hash, 'escritorio', 1, :now, :now)
    """), {
        "id": str(uuid.uuid4()), "tenant_id": tenant_id, "escritorio_id": office.id, "codigo": office.codigo,
        "nome": office.nome, "email": body.emailAcesso,
        "senha_hash": bcrypt.hashpw(body.senhaInicial.encode(), bcrypt.gensalt()).decode(), "now": datetime.utcnow(),
    })
    db.commit()
    return {"ok": True, "escritorioId": office.id, "email": body.emailAcesso}

@router.post("/v1/lex/escritorios", status_code=201)
def create_escritorio(body: EscritorioIn, db: Session = Depends(get_db), payload=Depends(verify_token)):
    tenant_id = payload.get("tenant_id") or payload.get("sub")
    if payload.get("role") == "admin":
        if not body.emailAcesso or not body.senhaInicial:
            raise HTTPException(400, "Informe o e-mail e a senha inicial da conta do escritÃ³rio")
        if len(body.senhaInicial) < 6:
            raise HTTPException(400, "A senha inicial precisa ter pelo menos 6 caracteres")
        if body.limiteAdvogados < 1:
            raise HTTPException(400, "O limite de advogados precisa ser maior que zero")
        if db.execute(text("SELECT id FROM usuarios WHERE email = :email"), {"email": body.emailAcesso}).first():
            raise HTTPException(409, "E-mail jÃ¡ cadastrado")
    if payload.get("role") != "admin":
        if payload.get("role") != "advogado":
            raise HTTPException(403, "Acesso negado")
        tenant = db.execute(
            text("SELECT plano, trial_expires_at FROM tenants WHERE id = :tid"),
            {"tid": tenant_id},
        ).mappings().first()
        if not tenant or tenant["plano"] != "trial":
            raise HTTPException(403, "A criação de escritório pelo titular está disponível durante o trial")
        expires_at = tenant["trial_expires_at"]
        if expires_at and expires_at < datetime.utcnow():
            raise HTTPException(403, "Trial expirado. Assine um plano para criar o escritório")
        if db.query(Escritorio).filter_by(tenant_id=tenant_id).first():
            raise HTTPException(403, "Este tenant já possui um escritório cadastrado")
    codigo = None
    for _ in range(10):
        candidate = "KX-" + secrets.token_hex(6).upper()
        exists = db.execute(text("SELECT id FROM escritorios WHERE codigo = :codigo"), {"codigo": candidate}).first()
        if not exists:
            codigo = candidate
            break
    if not codigo:
        raise HTTPException(503, "Não foi possível gerar um código para o escritório. Tente novamente.")
    e = Escritorio(tenant_id=tenant_id, codigo=codigo, nome=body.nome, cnpj=body.cnpj,
                   endereco=body.endereco, telefone=body.telefone, email=body.email,
                   limite_advogados=body.limiteAdvogados if payload.get("role") == "admin" else 3)
    db.add(e); db.flush()
    if payload.get("role") == "admin":
        db.execute(text("""
            INSERT INTO usuarios (id, tenant_id, escritorio_id, codigo, nome, email, senha_hash, role, ativo, created_at, updated_at)
            VALUES (:id, :tenant_id, :escritorio_id, :codigo, :nome, :email, :senha_hash, 'escritorio', 1, :now, :now)
        """), {
            "id": str(uuid.uuid4()), "tenant_id": tenant_id, "escritorio_id": e.id, "codigo": e.codigo,
            "nome": body.nome, "email": body.emailAcesso,
            "senha_hash": bcrypt.hashpw(body.senhaInicial.encode(), bcrypt.gensalt()).decode(), "now": datetime.utcnow(),
        })
    db.commit(); db.refresh(e)
    return _to_dict(e)

@router.post("/v1/lex/escritorios/update")
def update_escritorio(body: EscritorioUpdate, db: Session = Depends(get_db), payload=Depends(require_admin)):
    tenant_id = payload.get("tenant_id") or payload.get("sub")
    e = db.query(Escritorio).filter_by(id=body.id, tenant_id=tenant_id).first()
    if not e:
        raise HTTPException(404, "Não encontrado")
    data = body.model_dump(exclude_none=True, exclude={"id"})
    limite_advogados = data.pop("limiteAdvogados", None)
    if limite_advogados is not None:
        if limite_advogados < 1:
            raise HTTPException(400, "O limite de advogados precisa ser maior que zero")
        e.limite_advogados = limite_advogados
    for k, v in data.items():
        setattr(e, k, v)
    e.updated_at = datetime.utcnow()
    db.commit(); db.refresh(e)
    usuarios_ativos, advogados_ativos = _usage_for_escritorio(db, e.id)
    return _to_dict(e, usuarios_ativos, advogados_ativos)


@router.post("/v1/lex/escritorios/delete")
def delete_escritorio(body: EscritorioDeleteIn, db: Session = Depends(get_db), payload=Depends(require_admin)):
    tenant_id = payload.get("tenant_id") or payload.get("sub")
    e = db.query(Escritorio).filter_by(id=body.id, tenant_id=tenant_id).first()
    if not e:
        raise HTTPException(404, "Não encontrado")
    db.delete(e); db.commit()
    return {"ok": True}

@router.post("/v1/lex/escritorios/associar-membro")
def associar_membro(body: MembroIn, db: Session = Depends(get_db), payload=Depends(require_admin)):
    """Associa ou desassocia um usuário a um escritório, respeitando a quota."""
    tenant_id = payload.get("tenant_id") or payload.get("sub")
    user = db.execute(
        text("SELECT id, escritorio_id, ativo FROM usuarios WHERE id = :uid AND tenant_id = :tid"),
        {"uid": body.usuarioId, "tid": tenant_id},
    ).mappings().first()
    if not user:
        raise HTTPException(404, "Usuário não encontrado")

    if body.escritorioId:
        office = db.execute(
            text("SELECT limite_advogados FROM escritorios WHERE id = :eid AND tenant_id = :tid FOR UPDATE"),
            {"eid": body.escritorioId, "tid": tenant_id},
        ).mappings().first()
        if not office:
            raise HTTPException(404, "Escritório não encontrado")
        if user["ativo"] and user["escritorio_id"] != body.escritorioId:
            count = db.execute(
                text("SELECT COUNT(*) FROM usuarios WHERE escritorio_id = :eid AND tenant_id = :tid AND ativo = 1 AND role = 'advogado'"),
                {"eid": body.escritorioId, "tid": tenant_id},
            ).scalar_one()
            limit = int(office["limite_advogados"])
            if count >= limit:
                raise HTTPException(400, f"Limite de {limit} advogados atingido para este escritório. Entre em contato com o suporte/admin para alterar o limite.")

    db.execute(
        text("UPDATE usuarios SET escritorio_id = :eid, codigo = (SELECT codigo FROM escritorios WHERE id = :eid), updated_at = NOW() WHERE id = :uid AND tenant_id = :tid"),
        {"eid": body.escritorioId, "uid": body.usuarioId, "tid": tenant_id}
    )
    db.commit()
    return {"ok": True, "usuarioId": body.usuarioId, "escritorioId": body.escritorioId,
            "modalidade": "escritorio" if body.escritorioId else "autonomo"}


@router.post("/v1/lex/escritorios/associar-codigo")
def associar_por_codigo(body: AssociarCodigoIn, db: Session = Depends(get_db), payload=Depends(verify_token)):
    if payload.get("role") != "advogado":
        raise HTTPException(403, "Somente advogados autônomos podem usar um código de associação")
    tenant_id = payload.get("tenant_id") or payload.get("sub")
    usuario_id = payload.get("sub")
    codigo = body.codigo.strip().upper()
    if not codigo or len(codigo) > 16:
        raise HTTPException(400, "Informe um código de escritório válido")
    user = db.execute(text("SELECT id, escritorio_id, ativo FROM usuarios WHERE id = :uid AND tenant_id = :tid AND role = 'advogado' FOR UPDATE"), {"uid": usuario_id, "tid": tenant_id}).mappings().first()
    if not user:
        raise HTTPException(404, "Usuário não encontrado")
    escritorio_atual = user["escritorio_id"]
    if escritorio_atual is not None and str(escritorio_atual).strip():
        raise HTTPException(409, "Você já está associado a um escritório. Solicite a alteração ao administrador.")
    office = db.execute(text("SELECT id, tenant_id, nome, limite_advogados FROM escritorios WHERE codigo = :codigo AND ativo = 1 FOR UPDATE"), {"codigo": codigo}).mappings().first()
    if not office:
        raise HTTPException(404, "Código não encontrado ou escritório inativo. Confira o código com o escritório.")
    count = db.execute(text("SELECT COUNT(*) FROM usuarios WHERE escritorio_id = :eid AND ativo = 1 AND role = 'advogado'"), {"eid": office["id"]}).scalar_one()
    limit = int(office["limite_advogados"])
    if user["ativo"] and count >= limit:
        raise HTTPException(409, f"Este escritório atingiu o limite de {limit} advogados. Entre em contato com o escritório para concluir a associação manualmente ou resolver a pendência de vagas.")
    updated = db.execute(
        text("UPDATE usuarios SET escritorio_id = :eid, codigo = :codigo, updated_at = NOW() WHERE id = :uid AND tenant_id = :tid AND (escritorio_id IS NULL OR TRIM(escritorio_id) = '')"),
        {"eid": office["id"], "codigo": codigo, "uid": usuario_id, "tid": tenant_id},
    )
    if updated.rowcount != 1:
        db.rollback()
        raise HTTPException(409, "Este advogado jÃ¡ estÃ¡ associado a um escritÃ³rio.")
    db.commit()
    return {"ok": True, "usuarioId": usuario_id, "escritorioId": office["id"], "escritorioNome": office["nome"], "codigo": codigo, "modalidade": "escritorio"}
