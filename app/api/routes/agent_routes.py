from fastapi import APIRouter

from app.legacy_context import (
    AgenteIA,
    AgenteIACreate,
    AgenteIAUpdate,
    Depends,
    HTTPException,
    Session,
    _require_admin,
    _row,
    _validate_model_provider,
    datetime,
    get_db,
    verify_token,
)

router = APIRouter()


@router.get("/k1/lex/agentes")
def listar_agentes(db: Session = Depends(get_db), payload=Depends(_require_admin)):
    """Lista todos os agentes do tenant (apenas admin)"""
    tenant_id = payload.get("tenant_id")
    agentes = db.query(AgenteIA).filter(AgenteIA.tenant_id == tenant_id).order_by(AgenteIA.created_at.desc()).all()
    return [{**_row(a)} for a in agentes]


@router.get("/k1/lex/agentes/publicos")
def listar_agentes_publicos(db: Session = Depends(get_db), payload=Depends(verify_token)):
    """Lista agentes publicos e ativos (disponiveis para todos)"""
    tenant_id = payload.get("tenant_id")
    agentes = db.query(AgenteIA).filter(
        AgenteIA.tenant_id == tenant_id,
        AgenteIA.ativo == True,
        AgenteIA.publico == True
    ).order_by(AgenteIA.created_at.desc()).all()
    public_agents = []
    for agent in agentes:
        item = _row(agent)
        item.pop("api_key", None)
        item["configured"] = bool(agent.api_key)
        public_agents.append(item)
    return public_agents


@router.get("/k1/lex/agentes/{agente_id}")
def buscar_agente_by_id(agente_id: str, db: Session = Depends(get_db), payload=Depends(verify_token)):
    """Busca um agente especifico por ID via GET"""
    tenant_id = payload.get("tenant_id")
    agente = db.query(AgenteIA).filter(
        AgenteIA.id == agente_id,
        AgenteIA.tenant_id == tenant_id
    ).first()
    
    if not agente:
        raise HTTPException(404, "Agente nao encontrado")
    
    if payload.get("role") != "admin" and not agente.publico:
        raise HTTPException(403, "Acesso negado a este agente")
    
    return _row(agente)


@router.put("/k1/lex/agentes/{agente_id}")
def atualizar_agente_by_id(agente_id: str, body: AgenteIAUpdate, db: Session = Depends(get_db), payload=Depends(_require_admin)):
    """Atualiza um agente via PUT"""
    tenant_id = payload.get("tenant_id")
    agente = db.query(AgenteIA).filter(
        AgenteIA.id == agente_id,
        AgenteIA.tenant_id == tenant_id
    ).first()
    
    if not agente:
        raise HTTPException(404, "Agente nao encontrado")
    
    update_data = body.model_dump(exclude_none=True)
    
    _validate_model_provider(update_data.get("provider", agente.provider), update_data.get("modelo", agente.modelo))
    
    if "api_key" in update_data:
        provider = update_data.get("provider", agente.provider)
        if provider == "cerebras" and not update_data["api_key"].startswith("csk-"):
            raise HTTPException(400, "API key Cerebras deve comecar com 'csk-'")
        if provider == "groq" and not (update_data["api_key"].startswith("gsk-") or update_data["api_key"].startswith("gsk_")):
            raise HTTPException(400, "API key Groq deve comecar com 'gsk-' ou 'gsk_'")
    
    for field, value in update_data.items():
        if hasattr(agente, field):
            setattr(agente, field, value)
    
    agente.updated_at = datetime.utcnow()
    db.commit()
    db.refresh(agente)
    
    return _row(agente)


@router.delete("/k1/lex/agentes/{agente_id}")
def deletar_agente_by_id(agente_id: str, db: Session = Depends(get_db), payload=Depends(_require_admin)):
    """Deleta um agente via DELETE"""
    tenant_id = payload.get("tenant_id")
    agente = db.query(AgenteIA).filter(
        AgenteIA.id == agente_id,
        AgenteIA.tenant_id == tenant_id
    ).first()
    
    if not agente:
        raise HTTPException(404, "Agente nao encontrado")
    
    db.delete(agente)
    db.commit()
    
    return {"ok": True}


@router.post("/k1/lex/agentes/get")
def buscar_agente(body: dict, db: Session = Depends(get_db), payload=Depends(verify_token)):
    """Busca um agente especifico"""
    agente_id = body.get("id")
    if not agente_id:
        raise HTTPException(400, "ID do agente obrigatorio")
    
    tenant_id = payload.get("tenant_id")
    agente = db.query(AgenteIA).filter(
        AgenteIA.id == agente_id,
        AgenteIA.tenant_id == tenant_id
    ).first()
    
    if not agente:
        raise HTTPException(404, "Agente nao encontrado")
    
    # Se nao for admin, so pode ver agentes publicos
    if payload.get("role") != "admin" and not agente.publico:
        raise HTTPException(403, "Acesso negado a este agente")
    
    return _row(agente)


@router.post("/k1/lex/agentes", status_code=201)
def criar_agente(body: AgenteIACreate, db: Session = Depends(get_db), payload=Depends(_require_admin)):
    """Cria um novo agente (apenas admin)"""
    # Validar provider
    _validate_model_provider(body.provider, body.modelo)
    
    # Validar prefixo da API key
    if body.provider == "cerebras" and not body.api_key.startswith("csk-"):
        raise HTTPException(400, "API key Cerebras deve comecar com 'csk-'")
    if body.provider == "groq" and not (body.api_key.startswith("gsk-") or body.api_key.startswith("gsk_")):
        raise HTTPException(400, "API key Groq deve comecar com 'gsk-' ou 'gsk_'")
    
    tenant_id = payload.get("tenant_id")
    escritorio_id = payload.get("escritorio_id")
    
    novo_agente = AgenteIA(
        tenant_id=tenant_id,
        escritorio_id=escritorio_id,
        **body.model_dump()
    )
    
    db.add(novo_agente)
    db.commit()
    db.refresh(novo_agente)
    
    return _row(novo_agente)


@router.post("/k1/lex/agentes/update")
def atualizar_agente(body: dict, db: Session = Depends(get_db), payload=Depends(_require_admin)):
    """Atualiza um agente existente (apenas admin)"""
    agente_id = body.get("id")
    if not agente_id:
        raise HTTPException(400, "ID do agente obrigatorio")
    
    tenant_id = payload.get("tenant_id")
    agente = db.query(AgenteIA).filter(
        AgenteIA.id == agente_id,
        AgenteIA.tenant_id == tenant_id
    ).first()
    
    if not agente:
        raise HTTPException(404, "Agente nao encontrado")
    
    # Remover 'id' dos dados de atualização
    update_data = {k: v for k, v in body.items() if k != "id" and v is not None}
    
    # Validar provider se fornecido
    _validate_model_provider(update_data.get("provider", agente.provider), update_data.get("modelo", agente.modelo))
    
    # Validar prefixo da API key se fornecida
    if "api_key" in update_data:
        provider = update_data.get("provider", agente.provider)
        if provider == "cerebras" and not update_data["api_key"].startswith("csk-"):
            raise HTTPException(400, "API key Cerebras deve comecar com 'csk-'")
        if provider == "groq" and not (update_data["api_key"].startswith("gsk-") or update_data["api_key"].startswith("gsk_")):
            raise HTTPException(400, "API key Groq deve comecar com 'gsk-' ou 'gsk_'")
    
    # Atualizar campos
    for field, value in update_data.items():
        if hasattr(agente, field):
            setattr(agente, field, value)
    
    agente.updated_at = datetime.utcnow()
    db.commit()
    db.refresh(agente)
    
    return _row(agente)


@router.post("/k1/lex/agentes/delete")
def deletar_agente(body: dict, db: Session = Depends(get_db), payload=Depends(_require_admin)):
    """Deleta um agente (apenas admin)"""
    agente_id = body.get("id")
    if not agente_id:
        raise HTTPException(400, "ID do agente obrigatorio")
    
    tenant_id = payload.get("tenant_id")
    agente = db.query(AgenteIA).filter(
        AgenteIA.id == agente_id,
        AgenteIA.tenant_id == tenant_id
    ).first()
    
    if not agente:
        raise HTTPException(404, "Agente nao encontrado")
    
    db.delete(agente)
    db.commit()
    
    return {"ok": True}
