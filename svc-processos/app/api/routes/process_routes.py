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
from app.infrastructure.database.models.processo_model import Cliente, Fase, Processo, ProcessClient
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
        requested_links = body.clientesVinculados or [{"clienteId": body.clienteId, "proceduralRole": "Interessado", "isPrimary": True}]
        if not any(link.get("clienteId") == body.clienteId and link.get("isPrimary") for link in requested_links):
            requested_links = [{"clienteId": body.clienteId, "proceduralRole": "Interessado", "isPrimary": True}, *requested_links]
        if sum(bool(link.get("isPrimary")) for link in requested_links) != 1:
            raise HTTPException(422, "O processo deve ter exatamente um cliente principal")
        if len({link.get("clienteId") for link in requested_links}) != len(requested_links):
            raise HTTPException(422, "Não repita clientes no mesmo processo")
        for link in requested_links:
            linked_query = db.query(Cliente).filter_by(id=link.get("clienteId"), tenant_id=tenant_id)
            if payload.get("role") == "advogado":
                linked_query = linked_query.filter_by(advogado_id=payload.get("sub"))
            linked_client = linked_query.first()
            if not linked_client:
                raise HTTPException(404, "Cliente vinculado não encontrado neste escritório")
            db.add(ProcessClient(
                id=str(uuid.uuid4()), tenant_id=tenant_id, processo_id=process_id,
                cliente_id=linked_client.id, posicao_processual=link.get("proceduralRole") or "Interessado",
                polo_processual=link.get("proceduralPole"), cliente_principal=int(bool(link.get("isPrimary"))),
                snapshot_qualificacao={"nome": linked_client.nome, "email": linked_client.email,
                    "telefone": linked_client.telefone, "cpfCnpj": linked_client.cpf_cnpj,
                    "cep": linked_client.cep, "endereco": linked_client.endereco,
                    "cidade": linked_client.cidade, "estado": linked_client.estado,
                    "rg": linked_client.rg, "orgaoExpedidor": linked_client.orgao_expedidor,
                    "nacionalidade": linked_client.nacionalidade, "estadoCivil": linked_client.estado_civil,
                    "profissao": linked_client.profissao, "dataNascimento": linked_client.data_nascimento,
                    "razaoSocial": linked_client.razao_social, "nomeFantasia": linked_client.nome_fantasia,
                    "inscricaoEstadual": linked_client.inscricao_estadual,
                    "inscricaoMunicipal": linked_client.inscricao_municipal,
                    "representanteLegal": linked_client.representante_legal, "whatsapp": linked_client.whatsapp},
                observacoes=link.get("notes"), criado_por=payload["sub"], ativo=1,
            ))
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
        
    except HTTPException:
        db.rollback()
        raise
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

