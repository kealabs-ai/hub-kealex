from fastapi import APIRouter

from app.legacy_context import (
    Cliente,
    Depends,
    Fase,
    HTTPException,
    Processo,
    ProcessoDeleteIn,
    ProcessoGetIn,
    ProcessoIn,
    ProcessoUpdate,
    Session,
    _enrich_processos,
    _processo_to_dict,
    datetime,
    get_db,
    uuid,
    verify_token,
)

router = APIRouter()


@router.get("/k1/lex/processos")
def list_processos(db: Session = Depends(get_db), payload=Depends(verify_token)):
    role, uid, tid = payload.get("role"), payload.get("sub"), payload.get("tenant_id")
    q = db.query(Processo).filter_by(tenant_id=tid)
    
    if role == "cliente":
        q = q.filter_by(cliente_id=uid)
    elif role in ("advogado", "juridico"):
        q = q.filter_by(advogado_id=uid)
    
    return _enrich_processos(db, q.all())


@router.post("/k1/lex/processos/get")
def get_processo(body: ProcessoGetIn, db: Session = Depends(get_db), payload=Depends(verify_token)):
    tenant_id = payload.get("tenant_id")
    p = db.query(Processo).filter_by(id=body.id, tenant_id=tenant_id).first()
    if not p:
        raise HTTPException(404, "Não encontrado")
    cliente = db.query(Cliente).filter_by(id=p.cliente_id).first()
    return _processo_to_dict(p, cliente, db)


@router.post("/k1/lex/processos", status_code=201)
def create_processo(body: ProcessoIn, db: Session = Depends(get_db), payload=Depends(verify_token)):
    tenant_id = payload.get("tenant_id")
    cliente = db.query(Cliente).filter_by(id=body.clienteId, tenant_id=tenant_id).first()
    if not cliente:
        raise HTTPException(404, "Cliente não encontrado")
    p = Processo(tenant_id=tenant_id, user_id=payload["sub"], escritorio_id=body.escritorioId,
                 numero=body.numero, titulo=body.titulo, descricao=body.descricao,
                 advogado_id=payload["sub"], cliente_id=body.clienteId, vara=body.vara, tribunal=body.tribunal)
    db.add(p)
    db.flush()
    
    fases_padrao = [
        Fase(id=str(uuid.uuid4()), processo_id=p.id, label="Protocolo", ordem=0, status="ativa"),
        Fase(id=str(uuid.uuid4()), processo_id=p.id, label="Citacao", ordem=1, status="futura"),
        Fase(id=str(uuid.uuid4()), processo_id=p.id, label="Contestacao", ordem=2, status="futura"),
        Fase(id=str(uuid.uuid4()), processo_id=p.id, label="Audiencia", ordem=3, status="futura"),
        Fase(id=str(uuid.uuid4()), processo_id=p.id, label="Sentenca", ordem=4, status="futura"),
        Fase(id=str(uuid.uuid4()), processo_id=p.id, label="Recurso", ordem=5, status="futura"),
        Fase(id=str(uuid.uuid4()), processo_id=p.id, label="Encerrado", ordem=6, status="futura"),
    ]
    for fase in fases_padrao:
        db.add(fase)
    db.commit()
    db.refresh(p)
    
    return _processo_to_dict(p, cliente, db)


@router.post("/k1/lex/processos/update")
def update_processo(body: ProcessoUpdate, db: Session = Depends(get_db), payload=Depends(verify_token)):
    tenant_id = payload.get("tenant_id")
    p = db.query(Processo).filter_by(id=body.id, tenant_id=tenant_id).first()
    if not p:
        raise HTTPException(404, "Não encontrado")
    for k, v in body.model_dump(exclude_none=True, exclude={"id"}).items():
        setattr(p, k, v)
    p.updated_at = datetime.utcnow()
    db.commit(); db.refresh(p)
    cliente = db.query(Cliente).filter_by(id=p.cliente_id).first()
    return _processo_to_dict(p, cliente, db)


@router.post("/k1/lex/processos/delete")
def delete_processo(body: ProcessoDeleteIn, db: Session = Depends(get_db), payload=Depends(verify_token)):
    tenant_id = payload.get("tenant_id")
    p = db.query(Processo).filter_by(id=body.id, tenant_id=tenant_id).first()
    if not p:
        raise HTTPException(404, "Não encontrado")
    db.delete(p); db.commit()
    return {"ok": True}


@router.post("/k1/lex/processos/avancar-fase")
def avancar_fase(body: dict, db: Session = Depends(get_db), payload=Depends(verify_token)):
    processo_id = body.get("processoId")
    if not processo_id:
        raise HTTPException(400, "processoId obrigatório")
    
    tenant_id = payload.get("tenant_id")
    p = db.query(Processo).filter_by(id=processo_id, tenant_id=tenant_id).first()
    if not p:
        raise HTTPException(404, "Processo não encontrado")
    
    fases = db.query(Fase).filter_by(processo_id=processo_id).order_by(Fase.ordem).all()
    if not fases:
        raise HTTPException(400, "Nenhuma fase encontrada para este processo")
    
    fase_atual = db.query(Fase).filter_by(processo_id=processo_id, status="ativa").first()
    
    if not fase_atual:
        proxima_fase = fases[0]
    else:
        idx = next((i for i, f in enumerate(fases) if f.id == fase_atual.id), -1)
        if idx == -1 or idx >= len(fases) - 1:
            raise HTTPException(400, "Nenhuma próxima fase disponível")
        proxima_fase = fases[idx + 1]
    
    if fase_atual:
        fase_atual.status = "concluida"
        fase_atual.data_conclusao = datetime.utcnow()
    
    proxima_fase.status = "ativa"
    proxima_fase.updated_at = datetime.utcnow()
    
    db.commit()
    
    return {
        "ok": True,
        "faseAnterior": {"id": fase_atual.id, "label": fase_atual.label, "status": "concluida"} if fase_atual else None,
        "faseAtual": {"id": proxima_fase.id, "label": proxima_fase.label, "status": "ativa"}
    }


@router.post("/k1/lex/processos/listar-fases")
def listar_fases(body: dict, db: Session = Depends(get_db), payload=Depends(verify_token)):
    processo_id = body.get("processoId") or body.get("processo_id")
    if not processo_id:
        raise HTTPException(400, "processoId obrigatorio")
    
    tenant_id = payload.get("tenant_id")
    p = db.query(Processo).filter_by(id=processo_id, tenant_id=tenant_id).first()
    if not p:
        raise HTTPException(404, "Processo nao encontrado")
    
    fases = db.query(Fase).filter_by(processo_id=processo_id).order_by(Fase.ordem).all()
    return [{"id": f.id, "label": f.label, "ordem": f.ordem, "status": f.status, "dataConclusao": f.data_conclusao.isoformat() if f.data_conclusao else None} for f in fases]
