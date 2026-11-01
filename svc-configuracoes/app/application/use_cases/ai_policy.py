import json
from datetime import datetime
from fastapi import HTTPException
from sqlalchemy import text as sql_text
from sqlalchemy.orm import Session
from app.application.use_cases.user_api_keys import _current_api_key_owner
from app.infrastructure.database.models.configuration_model import AIPlanPolicy, AIUserPolicy, AITokenUsage

def _json_items(value, default=None):
    try:
        parsed = json.loads(value) if value else default
        return parsed if isinstance(parsed, list) else (default or [])
    except (TypeError, ValueError):
        return default or []


def _plan_key(db: Session, tenant_id: str) -> str:
    try:
        value = db.execute(sql_text("SELECT plano FROM tenants WHERE id=:tenant_id"), {"tenant_id": tenant_id}).scalar()
        return str(value or "trial").lower()
    except Exception:
        db.rollback()
        return "trial"


def _effective_ai_policy(db: Session, payload: dict) -> dict:
    user_id, tenant_id = _current_api_key_owner(payload)
    role = str(payload.get("role") or "")
    plan_key = _plan_key(db, tenant_id)
    plan = db.query(AIPlanPolicy).filter_by(tenant_id=tenant_id, plan_key=plan_key).first()
    user = db.query(AIUserPolicy).filter_by(tenant_id=tenant_id, user_id=user_id).first()
    allowed_roles = _json_items(plan.allowed_roles, ["advogado"]) if plan else ["advogado"]
    models = _json_items(plan.allowed_models, []) if plan else []
    menus = _json_items(plan.allowed_menus, ["/processos", "/documentos", "/prazos", "/atividades", "/financeiro", "/cobranca", "/usuarios", "/equipe", "/clientes", "/intimacoes", "/audiencias", "/integracao-orgaos", "/ia", "/analise-documentos", "/meus-agents", "/configuracoes/ia"]) if plan else ["/processos", "/documentos", "/prazos", "/atividades", "/financeiro", "/cobranca", "/usuarios", "/equipe", "/clientes", "/intimacoes", "/audiencias", "/integracao-orgaos", "/ia", "/analise-documentos", "/meus-agents", "/configuracoes/ia"]
    if user and user.allowed_models is not None: models = _json_items(user.allowed_models, [])
    if user and user.allowed_menus is not None: menus = _json_items(user.allowed_menus, [])
    can_create = bool(plan and plan.can_create_agents and role in allowed_roles)
    if user and user.can_create_agents is not None: can_create = bool(user.can_create_agents)
    monthly_limit = user.monthly_token_limit if user and user.monthly_token_limit is not None else (plan.monthly_token_limit if plan else 0)
    max_agents = user.max_agents if user and user.max_agents is not None else (plan.max_agents if plan else 0)
    period = datetime.utcnow().strftime("%Y-%m")
    usage = db.query(AITokenUsage).filter_by(tenant_id=tenant_id, user_id=user_id, period=period).first()
    return {"plan_key": plan_key, "can_create_agents": can_create, "allowed_roles": allowed_roles, "max_agents": max_agents or 0, "allowed_models": models, "allowed_menus": menus, "monthly_token_limit": monthly_limit or 0, "fallback_provider": plan.fallback_provider if plan else None, "fallback_model": plan.fallback_model if plan else None, "tokens_used": usage.tokens_used if usage else 0}


def _model_allowed(policy: dict, provider: str, model: str) -> bool:
    allowed = policy.get("allowed_models") or []
    return not allowed or model in allowed or f"{provider}:{model}" in allowed


def _assert_ai_menu(db: Session, payload: dict, path: str):
    policy = _effective_ai_policy(db, payload)
    if path not in policy.get("allowed_menus", []):
        raise HTTPException(403, "Este recurso de IA nÃ£o estÃ¡ liberado no plano do usuÃ¡rio.")

