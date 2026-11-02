import json
from datetime import datetime

from fastapi import HTTPException
from sqlalchemy import text as sql_text
from sqlalchemy.orm import Session

from app.application.use_cases.api_keys import _current_api_key_owner
from app.infrastructure.database.models import AIPlanPolicy, AIUserPolicy, AITokenUsage


AI_DEFAULT_MENUS = [
    "/processos", "/documentos", "/prazos", "/atividades", "/financeiro",
    "/cobranca", "/usuarios", "/equipe", "/clientes", "/intimacoes",
    "/audiencias", "/integracao-orgaos", "/ia", "/analise-documentos",
    "/meus-agents", "/configuracoes/ia",
]

AI_DEFAULT_PLANS = [
    ("trial", "Trial"),
    ("starter", "Starter"),
    ("professional", "Professional"),
    ("enterprise", "Enterprise"),
]

def _ai_json_items(value, default):
    if not value:
        return list(default)
    try:
        parsed = json.loads(value)
    except (TypeError, ValueError):
        return list(default)
    return parsed if isinstance(parsed, list) else list(default)

def _ai_plan_key(db: Session, tenant_id: str) -> str:
    value = db.execute(
        sql_text("SELECT plano FROM tenants WHERE id=:tenant_id"),
        {"tenant_id": tenant_id},
    ).scalar()
    return str(value or "trial").strip().lower()

def _effective_ai_policy(db: Session, payload: dict) -> dict:
    user_id, tenant_id = _current_api_key_owner(db, payload)
    plan_key = _ai_plan_key(db, tenant_id)
    plan = db.query(AIPlanPolicy).filter_by(tenant_id=tenant_id, plan_key=plan_key).first()
    user = db.query(AIUserPolicy).filter_by(tenant_id=tenant_id, user_id=user_id).first()
    allowed_roles = _ai_json_items(plan.allowed_roles, ["advogado"]) if plan else ["advogado"]
    models = _ai_json_items(plan.allowed_models, []) if plan else []
    menus = _ai_json_items(plan.allowed_menus, AI_DEFAULT_MENUS) if plan else list(AI_DEFAULT_MENUS)
    if user and user.allowed_models is not None:
        models = _ai_json_items(user.allowed_models, [])
    if user and user.allowed_menus is not None:
        menus = _ai_json_items(user.allowed_menus, [])

    can_create_agents = bool(
        plan
        and plan.can_create_agents
        and str(payload.get("role") or "") in allowed_roles
    )
    if user and user.can_create_agents is not None:
        can_create_agents = bool(user.can_create_agents)

    token_period = datetime.utcnow().strftime("%Y-%m")
    usage = db.query(AITokenUsage).filter_by(
        tenant_id=tenant_id,
        user_id=user_id,
        period=token_period,
    ).first()
    return {
        "plan_key": plan_key,
        "can_create_agents": can_create_agents,
        "allowed_roles": allowed_roles,
        "max_agents": (
            user.max_agents if user and user.max_agents is not None
            else (plan.max_agents if plan else 0)
        ) or 0,
        "allowed_models": models,
        "allowed_menus": menus,
        "monthly_token_limit": (
            user.monthly_token_limit
            if user and user.monthly_token_limit is not None
            else (plan.monthly_token_limit if plan else 0)
        ) or 0,
        "fallback_provider": plan.fallback_provider if plan else None,
        "fallback_model": plan.fallback_model if plan else None,
        "tokens_used": usage.tokens_used if usage else 0,
    }

def _assert_ai_menu(db: Session, payload: dict, path: str):
    policy = _effective_ai_policy(db, payload)
    if path not in policy["allowed_menus"]:
        raise HTTPException(403, "Este recurso de IA não está liberado no plano do usuário.")

__all__ = ["AI_DEFAULT_MENUS", "AI_DEFAULT_PLANS", "_ai_json_items", "_ai_plan_key", "_effective_ai_policy", "_assert_ai_menu"]
