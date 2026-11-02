import logging
import uuid
from datetime import datetime
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import text
from sqlalchemy.orm import Session
from app.api.dependencies import auth_guard, verify_token
from app.api.schemas.process_schema import ProcessoIn, ProcessoGetIn, ProcessoUpdate, ProcessoDeleteIn, FaseIn, AvancarFaseIn
from app.application.use_cases.process_access import _scoped_process
from app.application.use_cases.process_presenter import _enrich, _to_dict
from app.application.use_cases.phase_queries import build_next_phases
from app.domain.entities.process_status import StatusEnum
from app.infrastructure.database.models.processo_model import Cliente, Fase, Processo
from app.infrastructure.database.session import get_db
logger = logging.getLogger(__name__)
router = APIRouter()

@router.get("/k1/lex/processos")
def list_processos(db: Session = Depends(get_db), payload=Depends(auth_guard)):
    role, uid, tid = payload.get("role"), payload.get("sub"), payload.get("tenant_id")
    q = db.query(Processo).filter_by(tenant_id=tid)
    
    if role == "cliente":
        q = q.filter_by(cliente_id=uid)
    elif role == "advogado":
        q = q.filter_by(advogado_id=uid, user_id=uid)
    elif role != "admin":
        raise HTTPException(403, "Acesso negado")
    
    return _enrich(db, q.all())

@router.post("/k1/lex/processos/get")
def get_processo(body: ProcessoGetIn, db: Session = Depends(get_db), payload=Depends(auth_guard)):
    tenant_id = payload.get("tenant_id")
    p = _scoped_process(db, body.id, payload)
    if not p:
        raise HTTPException(404, "Nao encontrado")
    cliente = db.query(Cliente).filter_by(id=p.cliente_id).first()
    return _to_dict(p, cliente)

@router.post("/k1/lex/processos", status_code=201)
def create_processo(body: ProcessoIn, db: Session = Depends(get_db), payload=Depends(auth_guard)):
    try:
        logger.info(f"[CREATE_PROCESSO] Iniciando criacao de processo: {body.numero}")
        tenant_id = payload.get("tenant_id")
        if payload.get("role") not in ("admin", "advogado"):
            raise HTTPException(403, "Acesso negado")
        logger.info(f"[CREATE_PROCESSO] Tenant ID: {tenant_id}")
        
        cliente_query = db.query(Cliente).filter_by(id=body.clienteId, tenant_id=tenant_id)
        if payload.get("role") == "advogado":
            cliente_query = cliente_query.filter_by(advogado_id=payload.get("sub"))
        cliente = cliente_query.first()
        if not cliente:
            logger.error(f"[CREATE_PROCESSO] Cliente nao encontrado: {body.clienteId}")
            raise HTTPException(404, "Cliente nao encontrado")
        logger.info(f"[CREATE_PROCESSO] Cliente encontrado: {cliente.nome}")
        
        processo_id = str(uuid.uuid4())
        logger.info(f"[CREATE_PROCESSO] Novo ID do processo: {processo_id}")
        
        p = Processo(
            id=processo_id,
            tenant_id=tenant_id,
            user_id=payload["sub"],
            escritorio_id=payload.get("escritorio_id") if payload.get("role") == "advogado" else None,
            numero=body.numero,
            titulo=body.titulo,
            descricao=body.descricao,
            status=StatusEnum.ativo,
            advogado_id=payload["sub"],
            cliente_id=body.clienteId,
            vara=body.vara,
            tribunal=body.tribunal,
            fase_atual=0
        )
        db.add(p)
        db.commit()
        logger.info(f"[CREATE_PROCESSO] Processo criado com sucesso: {processo_id}")
        
        fases_padrao = [
            Fase(id=str(uuid.uuid4()), processo_id=p.id, label="Protocolo", ordem=0, status="ativa"),
            Fase(id=str(uuid.uuid4()), processo_id=p.id, label="Citacao", ordem=1, status="futura"),
            Fase(id=str(uuid.uuid4()), processo_id=p.id, label="Contestacao", ordem=2, status="futura"),
            Fase(id=str(uuid.uuid4()), processo_id=p.id, label="Audiencia", ordem=3, status="futura"),
            Fase(id=str(uuid.uuid4()), processo_id=p.id, label="Sentenca", ordem=4, status="futura"),
            Fase(id=str(uuid.uuid4()), processo_id=p.id, label="Recurso", ordem=5, status="futura"),
            Fase(id=str(uuid.uuid4()), processo_id=p.id, label="Encerrado", ordem=6, status="futura"),
        ]
        logger.info(f"[CREATE_PROCESSO] Criando {len(fases_padrao)} fases para o processo {processo_id}")
        
        for i, fase in enumerate(fases_padrao):
            logger.debug(f"[CREATE_PROCESSO] Adicionando fase {i}: {fase.label} (ID: {fase.id}, processo_id: {fase.processo_id})")
            db.add(fase)
        
        logger.info(f"[CREATE_PROCESSO] Fazendo commit das fases...")
        db.commit()
        logger.info(f"[CREATE_PROCESSO] Fases criadas com sucesso")
        
        db.refresh(p)
        logger.info(f"[CREATE_PROCESSO] Processo atualizado recuperado do banco")
        
        fases_verificacao = db.query(Fase).filter_by(processo_id=p.id).all()
        logger.info(f"[CREATE_PROCESSO] Verificacao: {len(fases_verificacao)} fases encontradas no banco")
        for fv in fases_verificacao:
            logger.debug(f"[CREATE_PROCESSO] Fase encontrada: {fv.label} (ID: {fv.id}, status: {fv.status})")
        
        resultado = _to_dict(p, cliente)
        logger.info(f"[CREATE_PROCESSO] Processo criado com sucesso com {len(resultado.get('fases', []))} fases")
        return resultado
        
    except Exception as e:
        logger.error(f"[CREATE_PROCESSO] ERRO: {str(e)}", exc_info=True)
        db.rollback()
        raise HTTPException(500, f"Erro ao criar processo: {str(e)}")

@router.post("/k1/lex/processos/update")
def update_processo(body: ProcessoUpdate, db: Session = Depends(get_db), payload=Depends(auth_guard)):
    tenant_id = payload.get("tenant_id")
    p = _scoped_process(db, body.id, payload)
    if not p:
        raise HTTPException(404, "Nao encontrado")
    for k, v in body.model_dump(exclude_none=True, exclude={"id"}).items():
        setattr(p, k, v)
    p.updated_at = datetime.utcnow()
    db.commit(); db.refresh(p)
    cliente = db.query(Cliente).filter_by(id=p.cliente_id).first()
    return _to_dict(p, cliente)

@router.post("/k1/lex/processos/delete")
def delete_processo(body: ProcessoDeleteIn, db: Session = Depends(get_db), payload=Depends(auth_guard)):
    tenant_id = payload.get("tenant_id")
    p = _scoped_process(db, body.id, payload)
    if not p:
        raise HTTPException(404, "Nao encontrado")
    db.delete(p); db.commit()
    return {"ok": True}

