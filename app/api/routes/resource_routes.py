from fastapi import APIRouter

from app.legacy_context import (
    Audiencia,
    AudienciaIn,
    AudienciaUpdateIn,
    Cliente,
    Depends,
    Documento,
    Fase,
    HTTPException,
    Honorario,
    Intimacao,
    IntimacaoIn,
    IntimacaoUpdateIn,
    KEALEX_DATABASE_URL,
    Prazo,
    Processo,
    ProcessoDeleteIn,
    Session,
    Usuario,
    _audiencia_to_dict,
    _intimacao_to_dict,
    _require_admin,
    datetime,
    get_db,
    make_url,
    uuid,
    verify_token,
)

router = APIRouter()


@router.get("/k1/lex/debug/fases/{processo_id}")
def debug_fases(processo_id: str, db: Session = Depends(get_db), payload=Depends(verify_token)):
    tenant_id = payload.get("tenant_id")
    p = db.query(Processo).filter_by(id=processo_id, tenant_id=tenant_id).first()
    if not p:
        return {"erro": "Processo nao encontrado", "processo_id": processo_id}
    
    fases = db.query(Fase).filter_by(processo_id=processo_id).all()
    return {
        "processo_id": processo_id,
        "processo_numero": p.numero,
        "total_fases": len(fases),
        "fases": [{"id": f.id, "label": f.label, "ordem": f.ordem, "status": f.status} for f in fases]
    }


@router.get("/clientes")
@router.get("/k1/lex/clientes")
def list_clientes(db: Session = Depends(get_db), payload=Depends(verify_token)):
    tenant_id = payload.get("tenant_id")
    return [{"id": c.id, "tenantId": c.tenant_id, "nome": c.nome, "email": c.email} for c in db.query(Cliente).filter_by(tenant_id=tenant_id).all()]


@router.post("/clientes", status_code=201)
@router.post("/k1/lex/clientes", status_code=201)
def create_cliente(body: dict, db: Session = Depends(get_db), payload=Depends(verify_token)):
    tenant_id = payload.get("tenant_id")
    c = Cliente(id=str(uuid.uuid4()), tenant_id=tenant_id, advogado_id=payload["sub"],
                nome=body.get("nome"), email=body.get("email"))
    db.add(c); db.commit(); db.refresh(c)
    return {"id": c.id, "tenantId": c.tenant_id, "nome": c.nome, "email": c.email}


@router.get("/documentos")
@router.get("/k1/lex/documentos")
def list_documentos(db: Session = Depends(get_db), payload=Depends(verify_token)):
    tenant_id = payload.get("tenant_id")
    docs = db.query(Documento).filter_by(tenant_id=tenant_id).all()
    return [{"id": d.id, "nome": d.nome, "tipo": d.tipo, "status": d.status, "processoId": d.processo_id} for d in docs]


@router.post("/documentos", status_code=201)
@router.post("/k1/lex/documentos", status_code=201)
def create_documento(body: dict, db: Session = Depends(get_db), payload=Depends(verify_token)):
    tenant_id = payload.get("tenant_id")
    d = Documento(
        id=str(uuid.uuid4()),
        tenant_id=tenant_id,
        user_id=payload["sub"],
        processo_id=body.get("processoId"),
        nome=body.get("nome"),
        tipo=body.get("tipo", "outro"),
        url_arquivo=body.get("urlArquivo", ""),
        status="pendente",
        tamanho_bytes=body.get("tamanhoBytes", 0)
    )
    db.add(d)
    db.commit()
    db.refresh(d)
    return {"id": d.id, "tenantId": d.tenant_id, "nome": d.nome, "tipo": d.tipo, "status": d.status}


@router.get("/financeiro")
@router.get("/k1/lex/financeiro")
def list_financeiro(db: Session = Depends(get_db), payload=Depends(verify_token)):
    tenant_id = payload.get("tenant_id")
    honorarios = db.query(Honorario).filter_by(tenant_id=tenant_id).all()
    return [{"id": h.id, "descricao": h.descricao, "valorCentavos": h.valor_centavos, "status": h.status, "processoId": h.processo_id} for h in honorarios]


@router.post("/financeiro", status_code=201)
@router.post("/k1/lex/financeiro", status_code=201)
def create_honorario(body: dict, db: Session = Depends(get_db), payload=Depends(verify_token)):
    tenant_id = payload.get("tenant_id")
    h = Honorario(
        id=str(uuid.uuid4()),
        tenant_id=tenant_id,
        user_id=payload["sub"],
        processo_id=body.get("processoId"),
        cliente_id=body.get("clienteId"),
        descricao=body.get("descricao", ""),
        valor_centavos=body.get("valorCentavos", 0),
        status="pendente"
    )
    db.add(h)
    db.commit()
    db.refresh(h)
    return {"id": h.id, "tenantId": h.tenant_id, "descricao": h.descricao, "valorCentavos": h.valor_centavos, "status": h.status}


@router.get("/financeiro/dashboard")
@router.get("/k1/lex/financeiro/dashboard")
def financeiro_dashboard(db: Session = Depends(get_db), payload=Depends(verify_token)):
    tenant_id = payload.get("tenant_id")
    honorarios = db.query(Honorario).filter_by(tenant_id=tenant_id).all()
    total_pago = sum(h.valor_centavos for h in honorarios if h.status == "pago")
    total_pendente = sum(h.valor_centavos for h in honorarios if h.status == "pendente")
    total_vencido = sum(h.valor_centavos for h in honorarios if h.status == "vencido")
    return {"totalPago": total_pago, "totalPendente": total_pendente, "totalVencido": total_vencido, "totalGeral": total_pago + total_pendente + total_vencido}


@router.get("/prazos")
@router.get("/k1/lex/prazos")
def list_prazos(db: Session = Depends(get_db), payload=Depends(verify_token)):
    tenant_id = payload.get("tenant_id")
    prazos = db.query(Prazo).filter_by(tenant_id=tenant_id).all()
    return [{"id": p.id, "titulo": p.titulo, "dataVencimento": p.data_vencimento, "status": p.status, "processoId": p.processo_id} for p in prazos]


@router.post("/prazos", status_code=201)
@router.post("/k1/lex/prazos", status_code=201)
def create_prazo(body: dict, db: Session = Depends(get_db), payload=Depends(verify_token)):
    tenant_id = payload.get("tenant_id")
    p = Prazo(
        id=str(uuid.uuid4()),
        tenant_id=tenant_id,
        user_id=payload["sub"],
        processo_id=body.get("processoId"),
        titulo=body.get("titulo"),
        descricao=body.get("descricao", ""),
        data_vencimento=body.get("dataVencimento"),
        status="pendente"
    )
    db.add(p)
    db.commit()
    db.refresh(p)
    return {"id": p.id, "tenantId": p.tenant_id, "titulo": p.titulo, "dataVencimento": p.data_vencimento, "status": p.status}


@router.post("/prazos/vencendo")
@router.post("/k1/lex/prazos/vencendo")
def prazos_vencendo(body: dict = None, db: Session = Depends(get_db), payload=Depends(verify_token)):
    tenant_id = payload.get("tenant_id")
    dias = body.get("dias", 7) if body else 7
    from datetime import date, timedelta
    hoje = date.today().isoformat()
    limite = (date.today() + timedelta(days=dias)).isoformat()
    prazos = db.query(Prazo).filter(
        Prazo.tenant_id == tenant_id,
        Prazo.data_vencimento >= hoje,
        Prazo.data_vencimento <= limite,
        Prazo.status == "pendente"
    ).all()
    return [{"id": p.id, "titulo": p.titulo, "dataVencimento": p.data_vencimento, "diasRestantes": (date.fromisoformat(p.data_vencimento) - date.today()).days} for p in prazos]


@router.get("/intimacoes")
@router.get("/k1/lex/intimacoes")
def list_intimacoes(db: Session = Depends(get_db), payload=Depends(verify_token)):
    rows = db.query(Intimacao).filter_by(
        tenant_id=payload.get("tenant_id"),
    ).order_by(Intimacao.data_publicacao.desc(), Intimacao.created_at.desc()).all()
    return [_intimacao_to_dict(row) for row in rows]


@router.post("/intimacoes", status_code=201)
@router.post("/k1/lex/intimacoes", status_code=201)
def create_intimacao(body: IntimacaoIn, db: Session = Depends(get_db), payload=Depends(verify_token)):
    data = body.model_dump()
    row = Intimacao(
        id=str(uuid.uuid4()),
        tenant_id=payload.get("tenant_id"),
        user_id=payload.get("sub"),
        processo_id=data["processoId"],
        processo_numero=data["processoNumero"],
        processo_titulo=data["processoTitulo"],
        diario=data["diario"].strip(),
        data_publicacao=data["dataPublicacao"],
        conteudo=data["conteudo"],
        resumo_ia=data["resumoIA"],
        prazo_calculado=data["prazoCalculado"],
        status=data["status"],
    )
    db.add(row)
    db.commit()
    db.refresh(row)
    return _intimacao_to_dict(row)


@router.patch("/intimacoes/{intimacao_id}")
@router.patch("/k1/lex/intimacoes/{intimacao_id}")
def update_intimacao(intimacao_id: str, body: IntimacaoUpdateIn, db: Session = Depends(get_db), payload=Depends(verify_token)):
    row = db.query(Intimacao).filter_by(
        id=intimacao_id,
        tenant_id=payload.get("tenant_id"),
    ).first()
    if not row:
        raise HTTPException(404, "Intimação não encontrada")
    data = body.model_dump(exclude_unset=True)
    if not data:
        raise HTTPException(400, "Informe ao menos um campo para atualizar")
    fields = {
        "processoId": "processo_id",
        "processoNumero": "processo_numero",
        "processoTitulo": "processo_titulo",
        "dataPublicacao": "data_publicacao",
        "resumoIA": "resumo_ia",
        "prazoCalculado": "prazo_calculado",
    }
    for name, value in data.items():
        if name in {"diario", "dataPublicacao", "conteudo", "status"} and value is None:
            raise HTTPException(400, f"O campo {name} não pode ser nulo")
        if name == "diario":
            value = value.strip()
        setattr(row, fields.get(name, name), value)
    row.updated_at = datetime.utcnow()
    db.commit()
    db.refresh(row)
    return _intimacao_to_dict(row)


@router.delete("/intimacoes/{intimacao_id}")
@router.delete("/k1/lex/intimacoes/{intimacao_id}")
def delete_intimacao(intimacao_id: str, db: Session = Depends(get_db), payload=Depends(verify_token)):
    row = db.query(Intimacao).filter_by(
        id=intimacao_id,
        tenant_id=payload.get("tenant_id"),
    ).first()
    if not row:
        raise HTTPException(404, "Intimação não encontrada")
    db.delete(row)
    db.commit()
    return {"ok": True}


@router.get("/audiencias")
@router.get("/k1/lex/audiencias")
def list_audiencias(db: Session = Depends(get_db), payload=Depends(verify_token)):
    tenant_id = payload.get("tenant_id")
    rows = db.query(Audiencia).filter_by(tenant_id=tenant_id).order_by(Audiencia.data_hora.asc()).all()
    return [_audiencia_to_dict(row) for row in rows]


@router.post("/audiencias", status_code=201)
@router.post("/k1/lex/audiencias", status_code=201)
def create_audiencia(body: AudienciaIn, db: Session = Depends(get_db), payload=Depends(verify_token)):
    row = Audiencia(
        tenant_id=payload.get("tenant_id"), user_id=payload.get("sub"),
        processo_id=body.processoId or None, processo_titulo=body.processoTitulo,
        tipo=body.tipo, data_hora=body.dataHora, local=body.local,
        juiz=body.juiz, partes=body.partes, observacoes=body.observacoes,
        roteiro=body.roteiro, status=body.status or "agendada",
    )
    db.add(row)
    db.commit()
    db.refresh(row)
    return _audiencia_to_dict(row)


@router.post("/audiencias/update")
@router.post("/k1/lex/audiencias/update")
def update_audiencia(body: AudienciaUpdateIn, db: Session = Depends(get_db), payload=Depends(verify_token)):
    row = db.query(Audiencia).filter_by(id=body.id, tenant_id=payload.get("tenant_id")).first()
    if not row:
        raise HTTPException(404, "Audiência não encontrada")
    data = body.model_dump(exclude_unset=True, exclude={"id"})
    fields = {"processoId": "processo_id", "processoTitulo": "processo_titulo", "dataHora": "data_hora"}
    for name, value in data.items():
        setattr(row, fields.get(name, name), value or None if name in {"juiz", "partes", "observacoes", "roteiro"} else value)
    row.updated_at = datetime.utcnow()
    db.commit()
    db.refresh(row)
    return _audiencia_to_dict(row)


@router.post("/audiencias/delete")
@router.post("/k1/lex/audiencias/delete")
def delete_audiencia(body: ProcessoDeleteIn, db: Session = Depends(get_db), payload=Depends(verify_token)):
    row = db.query(Audiencia).filter_by(id=body.id, tenant_id=payload.get("tenant_id")).first()
    if not row:
        raise HTTPException(404, "Audiência não encontrada")
    db.delete(row)
    db.commit()
    return {"ok": True}


@router.get("/usuarios")
@router.get("/k1/lex/usuarios")
def list_usuarios(db: Session = Depends(get_db), payload=Depends(verify_token)):
    tenant_id = payload.get("tenant_id")
    return [{"id": u.id, "tenantId": u.tenant_id, "nome": u.nome, "email": u.email, "role": u.role} for u in db.query(Usuario).filter_by(tenant_id=tenant_id).all()]


@router.get("/escritorios")
@router.get("/k1/lex/escritorios")
def list_escritorios(db: Session = Depends(get_db), payload=Depends(verify_token)):
    return {"data": [], "message": "Escritórios - use serviço svc-escritorios"}


@router.get("/configuracoes/geral")
@router.get("/k1/lex/configuracoes/geral")
def get_configuracoes_geral(db: Session = Depends(get_db), payload=Depends(verify_token)):
    tenant_id = payload.get("tenant_id")
    return {
        "tenantId": tenant_id,
        "theme": "light",
        "language": "pt-BR",
        "timezone": "America/Sao_Paulo",
        "notificacoes": True
    }


@router.post("/configuracoes/geral")
@router.post("/k1/lex/configuracoes/geral")
def save_configuracoes_geral(body: dict, db: Session = Depends(get_db), payload=Depends(verify_token)):
    return {"success": True, "message": "Configurações salvas", "data": body}


@router.get("/k1/lex/admin/config/env")
def get_database_env(payload=Depends(_require_admin)):
    """Retorna valores das variáveis de ambiente do banco de dados"""
    database_url = make_url(KEALEX_DATABASE_URL)
    return {
        "host": database_url.host or "",
        "port": str(database_url.port or ""),
        "name": database_url.database or "",
        "user": database_url.username or "",
        "password": "********" if database_url.password else "",
        "connection_string": database_url.render_as_string(hide_password=True),
    }
