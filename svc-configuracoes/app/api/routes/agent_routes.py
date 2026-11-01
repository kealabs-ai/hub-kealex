import json
import os
import re
import urllib.error
import urllib.request
import uuid
from datetime import datetime, timedelta
from typing import Optional
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import text as sql_text
from sqlalchemy.engine import make_url
from sqlalchemy.orm import Session
from google.oauth2.service_account import Credentials
from googleapiclient.discovery import build
from googleapiclient.errors import HttpError
from app.api.dependencies import require_admin, verify_token
from app.application.use_cases.configuration_support import _get_or_create, _row, _upsert
from app.application.use_cases.ai_catalog import MODELOS_DISPONIVEIS, IA_DEFAULT_MODELS, _validate_model_provider
from app.application.use_cases.ai_policy import _assert_ai_menu, _effective_ai_policy, _json_items, _model_allowed, _plan_key
from app.application.use_cases.user_api_keys import _current_api_key_owner, _decrypt_user_api_key, _encrypt_user_api_key, _user_api_key_json, _validate_user_api_key
from app.infrastructure.database.models.configuration_model import AIPlanPolicy, AIUserPolicy, AITokenUsage, AgenteIA, CfgCdn, CfgDatabase, CfgGeral, CfgIa, CfgIaProvider, CfgNotificacoes, CfgSeguranca, CfgUsuarios, DriveSource, IndexacaoArquivos, UserApiKey
from app.infrastructure.database.session import get_db
from app.api.schemas.agent_schema import AgenteIACreate, AgenteIAUpdate, PersonalAgentIn, AIPlanPolicyIn, AIUserPolicyIn

router = APIRouter()



@router.get("/k1/lex/agentes")
def listar_agentes(db: Session = Depends(get_db), payload=Depends(require_admin)):
    """Lista todos os agentes do tenant (apenas admin)"""
    tenant_id = payload.get("tenant_id") or payload.get("sub")
    agentes = db.query(AgenteIA).filter(AgenteIA.tenant_id == tenant_id).order_by(AgenteIA.created_at.desc()).all()
    return [{**_row(a)} for a in agentes]

@router.get("/k1/lex/agentes/publicos")
def listar_agentes_publicos(db: Session = Depends(get_db), payload=Depends(verify_token)):
    """Lista agentes pÃºblicos e ativos (disponÃ­veis para todos)"""
    tenant_id = payload.get("tenant_id") or payload.get("sub")
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



@router.get("/k1/lex/ia/politica")
def get_effective_ai_policy(db: Session = Depends(get_db), payload=Depends(verify_token)):
    return _effective_ai_policy(db, payload)




@router.get("/k1/lex/ia/admin/politicas")
def list_ai_plan_policies(db: Session = Depends(get_db), payload=Depends(require_admin)):
    tenant_id = payload.get("tenant_id") or payload.get("sub")
    saved = {row.plan_key: row for row in db.query(AIPlanPolicy).filter_by(tenant_id=tenant_id).all()}
    plans = [("trial", "Trial"), ("starter", "Starter"), ("professional", "Professional"), ("enterprise", "Enterprise")]
    known_plans = db.execute(sql_text("SELECT DISTINCT plano FROM tenants WHERE plano IS NOT NULL")).scalars().all()
    for known_plan in known_plans:
        key = str(known_plan or "").strip().lower()
        if key and key not in {plan_key for plan_key, _ in plans}: plans.append((key, key.replace("_", " ").title()))
    return [{"plan_key": key, "plan_label": label, "can_create_agents": bool(saved[key].can_create_agents) if key in saved else False, "allowed_roles": _json_items(saved[key].allowed_roles, ["advogado"]) if key in saved else ["advogado"], "max_agents": saved[key].max_agents if key in saved else 0, "allowed_models": _json_items(saved[key].allowed_models, []) if key in saved else [], "allowed_menus": _json_items(saved[key].allowed_menus, ["/processos", "/documentos", "/prazos", "/atividades", "/financeiro", "/cobranca", "/usuarios", "/equipe", "/clientes", "/intimacoes", "/audiencias", "/integracao-orgaos", "/ia", "/analise-documentos", "/meus-agents", "/configuracoes/ia"]) if key in saved else ["/processos", "/documentos", "/prazos", "/atividades", "/financeiro", "/cobranca", "/usuarios", "/equipe", "/clientes", "/intimacoes", "/audiencias", "/integracao-orgaos", "/ia", "/analise-documentos", "/meus-agents", "/configuracoes/ia"], "monthly_token_limit": saved[key].monthly_token_limit if key in saved else 0, "fallback_provider": saved[key].fallback_provider if key in saved else None, "fallback_model": saved[key].fallback_model if key in saved else None} for key, label in plans]


@router.put("/k1/lex/ia/admin/politicas/{plan_key}")
def save_ai_plan_policy(plan_key: str, body: AIPlanPolicyIn, db: Session = Depends(get_db), payload=Depends(require_admin)):
    tenant_id = payload.get("tenant_id") or payload.get("sub")
    plan_key = plan_key.strip().lower()
    if not re.fullmatch(r"[a-z0-9][a-z0-9_-]{0,39}", plan_key):
        raise HTTPException(400, "Identificador de plano invÃ¡lido.")
    known_plan = db.execute(
        sql_text("SELECT 1 FROM tenants WHERE LOWER(plano)=:plan_key LIMIT 1"),
        {"plan_key": plan_key},
    ).scalar()
    if plan_key not in {"trial", "starter", "professional", "enterprise"} and not known_plan:
        raise HTTPException(400, "Plano invÃ¡lido.")
    if body.max_agents < 0 or body.monthly_token_limit < 0: raise HTTPException(400, "Limites nÃ£o podem ser negativos.")
    row = db.query(AIPlanPolicy).filter_by(tenant_id=tenant_id, plan_key=plan_key).first()
    if not row:
        row = AIPlanPolicy(tenant_id=tenant_id, plan_key=plan_key)
        db.add(row)
    for field in ("can_create_agents", "max_agents", "monthly_token_limit", "fallback_provider", "fallback_model"): setattr(row, field, getattr(body, field))
    row.allowed_roles = json.dumps(body.allowed_roles)
    row.allowed_models = json.dumps(body.allowed_models)
    row.allowed_menus = json.dumps(body.allowed_menus)
    db.commit()
    return {"plan_key": plan_key, **body.model_dump()}




@router.get("/k1/lex/ia/admin/usuarios/{user_id}")
def get_ai_user_policy(user_id: str, db: Session = Depends(get_db), payload=Depends(require_admin)):
    tenant_id = payload.get("tenant_id") or payload.get("sub")
    user_exists = db.execute(
        sql_text("SELECT 1 FROM usuarios WHERE id=:user_id AND tenant_id=:tenant_id LIMIT 1"),
        {"user_id": user_id, "tenant_id": tenant_id},
    ).scalar()
    if not user_exists: raise HTTPException(404, "UsuÃ¡rio nÃ£o encontrado neste tenant.")
    row = db.query(AIUserPolicy).filter_by(tenant_id=tenant_id, user_id=user_id).first()
    if not row: return {"user_id": user_id, "can_create_agents": None, "max_agents": None, "monthly_token_limit": None, "allowed_models": None, "allowed_menus": None}
    return {"user_id": user_id, "can_create_agents": row.can_create_agents, "max_agents": row.max_agents, "monthly_token_limit": row.monthly_token_limit, "allowed_models": _json_items(row.allowed_models, []) if row.allowed_models else None, "allowed_menus": _json_items(row.allowed_menus, []) if row.allowed_menus else None}

@router.put("/k1/lex/ia/admin/usuarios/{user_id}")
def save_ai_user_policy(user_id: str, body: AIUserPolicyIn, db: Session = Depends(get_db), payload=Depends(require_admin)):
    tenant_id = payload.get("tenant_id") or payload.get("sub")
    user_exists = db.execute(
        sql_text("SELECT 1 FROM usuarios WHERE id=:user_id AND tenant_id=:tenant_id LIMIT 1"),
        {"user_id": user_id, "tenant_id": tenant_id},
    ).scalar()
    if not user_exists: raise HTTPException(404, "UsuÃ¡rio nÃ£o encontrado neste tenant.")
    if any(value is not None and value < 0 for value in (body.max_agents, body.monthly_token_limit)):
        raise HTTPException(400, "Limites nÃ£o podem ser negativos.")
    row = db.query(AIUserPolicy).filter_by(tenant_id=tenant_id, user_id=user_id).first()
    if not row:
        row = AIUserPolicy(tenant_id=tenant_id, user_id=user_id)
        db.add(row)
    values = body.model_dump(exclude_unset=True)
    for field in ("allowed_models", "allowed_menus"):
        if field in values and values[field] is not None: values[field] = json.dumps(values[field])
    for field, value in values.items(): setattr(row, field, value)
    db.commit()
    return {"user_id": user_id, **values}


@router.get("/k1/lex/agentes/meus")
def list_my_agents(db: Session = Depends(get_db), payload=Depends(verify_token)):
    user_id, tenant_id = _current_api_key_owner(payload)
    _assert_ai_menu(db, payload, "/meus-agents")
    return [{**_row(agent), "api_key": None, "configured": bool(db.query(UserApiKey).filter_by(user_id=user_id, tenant_id=tenant_id, provider=agent.provider, model=agent.modelo, is_active=True).first())} for agent in db.query(AgenteIA).filter_by(tenant_id=tenant_id, owner_user_id=user_id).order_by(AgenteIA.created_at.desc()).all()]


@router.post("/k1/lex/agentes/meus", status_code=201)
def create_my_agent(body: PersonalAgentIn, db: Session = Depends(get_db), payload=Depends(verify_token)):
    user_id, tenant_id = _current_api_key_owner(payload)
    _assert_ai_menu(db, payload, "/meus-agents")
    policy = _effective_ai_policy(db, payload)
    if not policy["can_create_agents"]: raise HTTPException(403, "Seu plano nÃ£o permite criar agentes personalizados.")
    count = db.query(AgenteIA).filter_by(tenant_id=tenant_id, owner_user_id=user_id).count()
    if policy["max_agents"] > 0 and count >= policy["max_agents"]: raise HTTPException(403, "VocÃª atingiu o limite de agentes do seu plano.")
    _validate_model_provider(body.provider, body.modelo)
    if not _model_allowed(policy, body.provider, body.modelo): raise HTTPException(403, "O modelo nÃ£o estÃ¡ liberado no seu plano.")
    if not db.query(UserApiKey).filter_by(tenant_id=tenant_id, user_id=user_id, provider=body.provider, model=body.modelo, is_active=True).first(): raise HTTPException(400, "Cadastre sua chave de IA para este provedor e modelo antes de criar o agente.")
    agent = AgenteIA(tenant_id=tenant_id, owner_user_id=user_id, created_by=user_id, escritorio_id=payload.get("escritorio_id"), nome=body.nome, descricao=body.descricao, provider=body.provider, modelo=body.modelo, max_tokens=body.max_tokens, system_prompt=body.system_prompt, ativo=body.ativo, publico=False, api_key=None)
    db.add(agent); db.commit(); db.refresh(agent)
    return {**_row(agent), "api_key": None, "configured": True}


@router.put("/k1/lex/agentes/meus/{agente_id}")
def update_my_agent(agente_id: str, body: PersonalAgentIn, db: Session = Depends(get_db), payload=Depends(verify_token)):
    user_id, tenant_id = _current_api_key_owner(payload)
    _assert_ai_menu(db, payload, "/meus-agents")
    agent = db.query(AgenteIA).filter_by(id=agente_id, tenant_id=tenant_id, owner_user_id=user_id).first()
    if not agent: raise HTTPException(404, "Agente nÃ£o encontrado.")
    policy = _effective_ai_policy(db, payload)
    _validate_model_provider(body.provider, body.modelo)
    if not _model_allowed(policy, body.provider, body.modelo): raise HTTPException(403, "O modelo nÃ£o estÃ¡ liberado no seu plano.")
    if not db.query(UserApiKey).filter_by(tenant_id=tenant_id, user_id=user_id, provider=body.provider, model=body.modelo, is_active=True).first(): raise HTTPException(400, "Cadastre sua chave de IA para este provedor e modelo antes de salvar.")
    for field, value in body.model_dump().items(): setattr(agent, field, value)
    agent.updated_at = datetime.utcnow(); db.commit(); db.refresh(agent)
    return {**_row(agent), "api_key": None, "configured": True}


@router.delete("/k1/lex/agentes/meus/{agente_id}", status_code=204)
def delete_my_agent(agente_id: str, db: Session = Depends(get_db), payload=Depends(verify_token)):
    user_id, tenant_id = _current_api_key_owner(payload)
    _assert_ai_menu(db, payload, "/meus-agents")
    agent = db.query(AgenteIA).filter_by(id=agente_id, tenant_id=tenant_id, owner_user_id=user_id).first()
    if not agent: raise HTTPException(404, "Agente nÃ£o encontrado.")
    db.delete(agent); db.commit()

@router.get("/k1/lex/agentes/{agente_id}")
def buscar_agente(agente_id: str, db: Session = Depends(get_db), payload=Depends(verify_token)):
    """Busca um agente especÃ­fico"""
    tenant_id = payload.get("tenant_id") or payload.get("sub")
    agente = db.query(AgenteIA).filter(
        AgenteIA.id == agente_id,
        AgenteIA.tenant_id == tenant_id
    ).first()
    
    if not agente:
        raise HTTPException(404, "Agente nÃ£o encontrado")
    
    # Se nÃ£o for admin, sÃ³ pode ver agentes pÃºblicos
    if payload.get("role") != "admin" and not agente.publico:
        raise HTTPException(403, "Acesso negado a este agente")
    
    return _row(agente)

@router.post("/k1/lex/agentes", status_code=201)
def criar_agente(body: AgenteIACreate, db: Session = Depends(get_db), payload=Depends(require_admin)):
    """Cria um novo agente (apenas admin)"""
    # Validar provider
    _validate_model_provider(body.provider, body.modelo)
    
    # Validar prefixo da API key
    if body.provider == "cerebras" and not body.api_key.startswith("csk-"):
        raise HTTPException(400, "API key Cerebras deve comeÃ§ar com 'csk-'")
    if body.provider == "groq" and not (body.api_key.startswith("gsk-") or body.api_key.startswith("gsk_")):
        raise HTTPException(400, "API key Groq deve comeÃ§ar com 'gsk-' ou 'gsk_'")
    
    tenant_id = payload.get("tenant_id") or payload.get("sub")
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

@router.put("/k1/lex/agentes/{agente_id}")
def atualizar_agente(agente_id: str, body: AgenteIAUpdate, db: Session = Depends(get_db), payload=Depends(require_admin)):
    """Atualiza um agente existente (apenas admin)"""
    tenant_id = payload.get("tenant_id") or payload.get("sub")
    agente = db.query(AgenteIA).filter(
        AgenteIA.id == agente_id,
        AgenteIA.tenant_id == tenant_id
    ).first()
    
    if not agente:
        raise HTTPException(404, "Agente nÃ£o encontrado")
    
    # Validar provider se fornecido
    update_data = body.model_dump(exclude_none=True)
    _validate_model_provider(update_data.get("provider", agente.provider), update_data.get("modelo", agente.modelo))
    
    # Validar prefixo da API key se fornecida
    if "api_key" in update_data:
        provider = update_data.get("provider", agente.provider)
        if provider == "cerebras" and not update_data["api_key"].startswith("csk-"):
            raise HTTPException(400, "API key Cerebras deve comeÃ§ar com 'csk-'")
        if provider == "groq" and not (update_data["api_key"].startswith("gsk-") or update_data["api_key"].startswith("gsk_")):
            raise HTTPException(400, "API key Groq deve comeÃ§ar com 'gsk-' ou 'gsk_'")
    
    # Atualizar campos
    for field, value in update_data.items():
        setattr(agente, field, value)
    
    agente.updated_at = datetime.utcnow()
    db.commit()
    db.refresh(agente)
    
    return _row(agente)

@router.delete("/k1/lex/agentes/{agente_id}", status_code=204)
def deletar_agente(agente_id: str, db: Session = Depends(get_db), payload=Depends(require_admin)):
    """Deleta um agente (apenas admin)"""
    tenant_id = payload.get("tenant_id") or payload.get("sub")
    agente = db.query(AgenteIA).filter(
        AgenteIA.id == agente_id,
        AgenteIA.tenant_id == tenant_id
    ).first()
    
    if not agente:
        raise HTTPException(404, "Agente nÃ£o encontrado")
    
    db.delete(agente)
    db.commit()
    
    return None

# â”€â”€ Google Drive â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€

