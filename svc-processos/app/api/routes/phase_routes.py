import logging
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

@router.post("/k1/lex/processos/avancar-fase")
def avancar_fase(body: AvancarFaseIn, db: Session = Depends(get_db), payload=Depends(auth_guard)):
    try:
        logger.info(f"[AVANCAR_FASE] Iniciando avanco de fase para processo: {body.processoId}, nova fase: {body.faseAtual}")
        tenant_id = payload.get("tenant_id")
        
        p = _scoped_process(db, body.processoId, payload)
        if not p:
            logger.error(f"[AVANCAR_FASE] Processo nao encontrado: {body.processoId}")
            raise HTTPException(404, "Processo nao encontrado")
        logger.info(f"[AVANCAR_FASE] Processo encontrado: {p.numero}")
        
        fases = db.query(Fase).filter_by(processo_id=p.id).order_by(Fase.ordem).all()
        logger.info(f"[AVANCAR_FASE] Total de fases encontradas: {len(fases)}")
        
        if not fases:
            logger.error(f"[AVANCAR_FASE] Nenhuma fase encontrada para o processo {body.processoId}")
            raise HTTPException(400, "Nenhuma fase encontrada para este processo")
        
        if body.faseAtual < 0 or body.faseAtual >= len(fases):
            logger.error(f"[AVANCAR_FASE] Fase invalida: {body.faseAtual}. Maximo: {len(fases) - 1}")
            raise HTTPException(400, f"Nenhuma próxima fase disponível")
        
        logger.info(f"[AVANCAR_FASE] Atualizando status das fases...")
        for i, fase in enumerate(fases):
            if i < body.faseAtual:
                fase.status = "concluida"
                if not fase.data_conclusao:
                    fase.data_conclusao = datetime.utcnow()
                logger.debug(f"[AVANCAR_FASE] Fase {i} ({fase.label}) marcada como concluida")
            elif i == body.faseAtual:
                fase.status = "ativa"
                logger.debug(f"[AVANCAR_FASE] Fase {i} ({fase.label}) marcada como ativa")
            else:
                fase.status = "futura"
                logger.debug(f"[AVANCAR_FASE] Fase {i} ({fase.label}) marcada como futura")
            db.add(fase)
        
        p.fase_atual = body.faseAtual
        p.updated_at = datetime.utcnow()
        db.add(p)
        logger.info(f"[AVANCAR_FASE] Fazendo commit das mudancas...")
        db.commit()
        logger.info(f"[AVANCAR_FASE] Avanco de fase realizado com sucesso")
        
        p_atualizado = db.query(Processo).filter_by(id=p.id).first()
        cliente = db.query(Cliente).filter_by(id=p_atualizado.cliente_id).first()
        return _to_dict(p_atualizado, cliente)
        
    except Exception as e:
        logger.error(f"[AVANCAR_FASE] ERRO: {str(e)}", exc_info=True)
        db.rollback()
        raise HTTPException(500, f"Erro ao avancar fase: {str(e)}")
@router.post("/k1/lex/processos/{processo_id}/proximas-fases")
def proximas_fases(processo_id: str, db: Session = Depends(get_db), payload=Depends(verify_token)):
    tenant_id = payload.get("tenant_id")
    p = _scoped_process(db, processo_id, payload)
    if not p:
        raise HTTPException(404, "Processo nao encontrado")
    
    fases = db.query(Fase).filter_by(processo_id=processo_id).order_by(Fase.ordem).all()
    return build_next_phases(fases, p.fase_atual)

@router.get("/k1/lex/processos/{processo_id}/debug-fases")
def debug_fases(processo_id: str, db: Session = Depends(get_db), payload=Depends(verify_token)):
    logger.info(f"[DEBUG_FASES] Verificando fases do processo: {processo_id}")
    tenant_id = payload.get("tenant_id")
    
    p = _scoped_process(db, processo_id, payload)
    if not p:
        logger.error(f"[DEBUG_FASES] Processo nao encontrado: {processo_id}")
        raise HTTPException(404, "Processo nao encontrado")
    
    logger.info(f"[DEBUG_FASES] Processo encontrado: {p.numero}")
    
    fases = db.query(Fase).filter_by(processo_id=processo_id).order_by(Fase.ordem).all()
    logger.info(f"[DEBUG_FASES] Total de fases encontradas: {len(fases)}")
    
    fases_info = []
    for f in fases:
        info = {
            "id": f.id,
            "processo_id": f.processo_id,
            "label": f.label,
            "ordem": f.ordem,
            "status": f.status,
            "data_conclusao": f.data_conclusao.isoformat() if f.data_conclusao else None,
            "created_at": f.created_at.isoformat(),
            "updated_at": f.updated_at.isoformat()
        }
        fases_info.append(info)
        logger.debug(f"[DEBUG_FASES] Fase: {info}")
    
    return {
        "processo_id": processo_id,
        "processo_numero": p.numero,
        "fase_atual": p.fase_atual,
        "total_fases": len(fases),
        "fases": fases_info
    }

