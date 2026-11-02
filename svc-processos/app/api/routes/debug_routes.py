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

@router.get("/k1/lex/debug/todas-fases")
def debug_todas_fases(db: Session = Depends(get_db), payload=Depends(verify_token)):
    logger.info(f"[DEBUG_TODAS_FASES] Verificando TODAS as fases do banco")
    
    todas_fases = db.query(Fase).all()
    logger.info(f"[DEBUG_TODAS_FASES] Total de fases no banco: {len(todas_fases)}")
    
    fases_info = []
    for f in todas_fases:
        info = {
            "id": f.id,
            "processo_id": f.processo_id,
            "label": f.label,
            "ordem": f.ordem,
            "status": f.status,
            "created_at": f.created_at.isoformat()
        }
        fases_info.append(info)
        logger.debug(f"[DEBUG_TODAS_FASES] Fase: {info}")
    
    return {
        "total_fases": len(todas_fases),
        "fases": fases_info
    }

@router.get("/k1/lex/debug/todos-processos")
def debug_todos_processos(db: Session = Depends(get_db), payload=Depends(verify_token)):
    logger.info(f"[DEBUG_TODOS_PROCESSOS] Verificando TODOS os processos do banco")
    tenant_id = payload.get("tenant_id")
    
    todos_processos = db.query(Processo).filter_by(tenant_id=tenant_id).all()
    logger.info(f"[DEBUG_TODOS_PROCESSOS] Total de processos encontrados: {len(todos_processos)}")
    
    processos_info = []
    for p in todos_processos:
        fases_count = db.query(Fase).filter_by(processo_id=p.id).count()
        info = {
            "id": p.id,
            "numero": p.numero,
            "titulo": p.titulo,
            "status": p.status,
            "fase_atual": p.fase_atual,
            "total_fases_no_banco": fases_count,
            "created_at": p.created_at.isoformat(),
            "updated_at": p.updated_at.isoformat()
        }
        processos_info.append(info)
        logger.info(f"[DEBUG_TODOS_PROCESSOS] Processo: {p.numero} - Fases no banco: {fases_count}")
    
    return {
        "tenant_id": tenant_id,
        "total_processos": len(todos_processos),
        "processos": processos_info
    }

@router.get("/k1/lex/debug/status-completo")
def debug_status_completo(db: Session = Depends(get_db), payload=Depends(verify_token)):
    logger.info(f"[DEBUG_STATUS_COMPLETO] Iniciando verificacao completa do sistema")
    tenant_id = payload.get("tenant_id")
    
    total_processos = db.query(Processo).filter_by(tenant_id=tenant_id).count()
    total_fases = db.query(Fase).count()
    total_clientes = db.query(Cliente).filter_by(tenant_id=tenant_id).count()
    
    logger.info(f"[DEBUG_STATUS_COMPLETO] Total de processos: {total_processos}")
    logger.info(f"[DEBUG_STATUS_COMPLETO] Total de fases: {total_fases}")
    logger.info(f"[DEBUG_STATUS_COMPLETO] Total de clientes: {total_clientes}")
    
    processos_sem_fases = []
    processos_com_fases = []
    
    todos_processos = db.query(Processo).filter_by(tenant_id=tenant_id).all()
    for p in todos_processos:
        fases_count = db.query(Fase).filter_by(processo_id=p.id).count()
        if fases_count == 0:
            processos_sem_fases.append({
                "id": p.id,
                "numero": p.numero,
                "titulo": p.titulo
            })
            logger.warning(f"[DEBUG_STATUS_COMPLETO] ALERTA: Processo {p.numero} SEM fases!")
        else:
            processos_com_fases.append({
                "id": p.id,
                "numero": p.numero,
                "titulo": p.titulo,
                "fases": fases_count
            })
            logger.info(f"[DEBUG_STATUS_COMPLETO] Processo {p.numero} com {fases_count} fases")
    
    return {
        "tenant_id": tenant_id,
        "resumo": {
            "total_processos": total_processos,
            "total_fases": total_fases,
            "total_clientes": total_clientes,
            "processos_com_fases": len(processos_com_fases),
            "processos_sem_fases": len(processos_sem_fases)
        },
        "processos_com_fases": processos_com_fases,
        "processos_sem_fases": processos_sem_fases
    }
