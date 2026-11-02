import json

from fastapi import APIRouter

from app.legacy_context import (
    AIPlanPolicy,
    AIPlanPolicyIn,
    AIUserPolicy,
    AIUserPolicyIn,
    AI_DEFAULT_MENUS,
    AI_DEFAULT_PLANS,
    AgenteIA,
    CfgIa,
    CfgIaProvider,
    Depends,
    HTTPException,
    IA_DEFAULT_MODELS,
    IaChatIn,
    IaIn,
    IaProviderIn,
    MODELOS_DISPONIVEIS,
    Session,
    UserApiKey,
    _ai_json_items,
    _current_api_key_owner,
    _decrypt_user_api_key,
    _effective_ai_policy,
    _get_or_create_cfg_ia,
    _openai_response,
    _provider_response,
    _require_admin,
    _row,
    _upsert_cfg_ia,
    _validate_model_provider,
    datetime,
    get_db,
    re,
    sql_text,
    verify_token,
)

router = APIRouter()


@router.get("/k1/lex/configuracoes/ia")
def get_ia(db: Session = Depends(get_db), payload=Depends(_require_admin)):
    tenant_id = payload.get("tenant_id") or payload.get("sub")
    user_id = payload.get("sub")
    active = _get_or_create_cfg_ia(db, tenant_id, user_id)
    provider_cfg = db.get(CfgIaProvider, (tenant_id, active.provider))
    result = _row(active)
    legacy_key = result.pop("api_key", None)
    result["configured"] = bool((provider_cfg.api_key if provider_cfg else None) or legacy_key)
    return result


@router.get("/k1/lex/configuracoes/ia/modelos")
def get_modelos_disponiveis():
    return MODELOS_DISPONIVEIS


@router.get("/k1/lex/configuracoes/ia/ativa")
def get_ia_ativa(db: Session = Depends(get_db), payload=Depends(verify_token)):
    tenant_id = payload.get("tenant_id") or payload.get("sub")
    user_id = payload.get("sub")
    active = _get_or_create_cfg_ia(db, tenant_id, user_id)
    provider_cfg = db.get(CfgIaProvider, (tenant_id, active.provider))
    result = _row(active)
    legacy_key = result.pop("api_key", None)
    result["configured"] = bool((provider_cfg.api_key if provider_cfg else None) or legacy_key)
    return result


@router.post("/k1/lex/configuracoes/ia")
def save_ia(body: IaIn, db: Session = Depends(get_db), payload=Depends(_require_admin)):
    data = body.model_dump(exclude_none=True)
    tenant_id = payload.get("tenant_id") or payload.get("sub")
    current = db.get(CfgIa, tenant_id)
    if "provider" in data or "modelo" in data:
        _validate_model_provider(data.get("provider") or (current.provider if current else "cerebras"), data.get("modelo") or (current.modelo if current else IA_DEFAULT_MODELS["cerebras"]))
    if "api_key" in data and data["api_key"]:
        tenant_id = payload.get("tenant_id") or payload.get("sub")
        existing = db.get(CfgIa, tenant_id)
        provider = data.get("provider") or (existing.provider if existing else "cerebras")
        if provider == "cerebras" and not data["api_key"].startswith("csk-"):
            raise HTTPException(400, "API key Cerebras deve comecar com 'csk-'")
        if provider == "groq" and not (data["api_key"].startswith("gsk-") or data["api_key"].startswith("gsk_")):
            raise HTTPException(400, "API key Groq deve comecar com 'gsk-' ou 'gsk_'")
    tenant_id = payload.get("tenant_id") or payload.get("sub")
    user_id = payload.get("sub")
    return _row(_upsert_cfg_ia(db, tenant_id, user_id, data))


@router.get("/k1/lex/configuracoes/ia/provedores")
def get_ia_provedores(db: Session = Depends(get_db), payload=Depends(_require_admin)):
    tenant_id = payload.get("tenant_id") or payload.get("sub")
    user_id = payload.get("sub")
    active = _get_or_create_cfg_ia(db, tenant_id, user_id)
    rows = db.query(CfgIaProvider).filter_by(tenant_id=tenant_id).all()
    configs = {}
    for row in rows:
        item = _row(row)
        item["configured"] = bool(item.pop("api_key", None))
        configs[row.provider] = item
    if active.provider not in configs:
        legacy = CfgIaProvider(tenant_id=tenant_id, user_id=user_id, provider=active.provider,
            api_key=active.api_key, modelo=active.modelo or IA_DEFAULT_MODELS.get(active.provider, ""),
            max_tokens=active.max_tokens or 8192, system_prompt=active.system_prompt, ativo=active.ativo)
        db.add(legacy)
        db.commit()
        db.refresh(legacy)
        item = _row(legacy)
        item["configured"] = bool(item.pop("api_key", None))
        configs[legacy.provider] = item
    return {"active_provider": active.provider, "providers": configs}


@router.post("/k1/lex/configuracoes/ia/provedores/{provider}")
def save_ia_provedor(provider: str, body: IaProviderIn, db: Session = Depends(get_db), payload=Depends(_require_admin)):
    if provider not in MODELOS_DISPONIVEIS:
        raise HTTPException(400, "Provider inválido")
    tenant_id = payload.get("tenant_id") or payload.get("sub")
    user_id = payload.get("sub")
    data = body.model_dump(exclude_none=True)
    current = db.get(CfgIaProvider, (tenant_id, provider))
    _validate_model_provider(provider, data.get("modelo") or (current.modelo if current else IA_DEFAULT_MODELS[provider]))
    if data.get("api_key") == "":
        data.pop("api_key")
    if "endpoint_url" in data:
        endpoint = data["endpoint_url"].strip().rstrip("/")
        if provider == "openai" and endpoint and endpoint != "https://api.openai.com/v1":
            raise HTTPException(400, "Use o endpoint oficial https://api.openai.com/v1 da OpenAI.")
        data["endpoint_url"] = endpoint or None
    row = db.get(CfgIaProvider, (tenant_id, provider))
    if row is None:
        row = CfgIaProvider(tenant_id=tenant_id, user_id=user_id, provider=provider, modelo=IA_DEFAULT_MODELS[provider])
        db.add(row)
    for key, value in data.items():
        setattr(row, key, value)
    row.updated_at = datetime.utcnow()
    active = db.get(CfgIa, tenant_id)
    if active and active.provider == provider:
        active.api_key, active.modelo = row.api_key, row.modelo
        active.max_tokens, active.system_prompt, active.ativo = row.max_tokens, row.system_prompt, row.ativo
        active.updated_at = datetime.utcnow()
    db.commit()
    db.refresh(row)
    result = _row(row)
    result["configured"] = bool(result.pop("api_key", None))
    return result


@router.post("/k1/lex/configuracoes/ia/provedor-ativo/{provider}")
def set_ia_provedor_ativo(provider: str, db: Session = Depends(get_db), payload=Depends(_require_admin)):
    if provider not in MODELOS_DISPONIVEIS:
        raise HTTPException(400, "Provider inválido")
    tenant_id = payload.get("tenant_id") or payload.get("sub")
    user_id = payload.get("sub")
    config = db.get(CfgIaProvider, (tenant_id, provider))
    if config is None or not config.api_key:
        raise HTTPException(400, "Configure a chave API deste provedor antes de ativá-lo")
    if not config.ativo:
        raise HTTPException(400, "Habilite este provedor antes de ativá-lo")
    active = _get_or_create_cfg_ia(db, tenant_id, user_id)
    active.provider, active.api_key, active.modelo = provider, config.api_key, config.modelo
    active.max_tokens, active.system_prompt, active.ativo = config.max_tokens, config.system_prompt, config.ativo
    active.updated_at = datetime.utcnow()
    db.commit()
    result = _row(active)
    result.pop("api_key", None)
    result["configured"] = True
    return result


@router.post("/k1/lex/configuracoes/ia/chat")
def chat_ia(body: IaChatIn, db: Session = Depends(get_db), payload=Depends(verify_token)):
    user_id, tenant_id = _current_api_key_owner(db, payload)
    personal_active = db.query(UserApiKey).filter_by(user_id=user_id, tenant_id=tenant_id, is_active=True).first()
    messages = [{"role": m.role, "content": m.content[:32000]} for m in body.messages[-50:] if m.role in ("user", "assistant")]
    if not messages or messages[-1]["role"] != "user":
        raise HTTPException(400, "A Ãºltima mensagem deve ser do usuÃ¡rio.")
    if body.agente_id:
        config = db.query(AgenteIA).filter_by(id=body.agente_id, tenant_id=tenant_id, ativo=True, publico=True).first()
        if not config:
            raise HTTPException(404, "Agente de IA nÃ£o encontrado.")
        provider, api_key, model = config.provider, config.api_key, config.modelo
        system_prompt, max_tokens, endpoint_url = config.system_prompt, config.max_tokens or 8192, None
        personal = db.query(UserApiKey).filter_by(user_id=user_id, tenant_id=tenant_id, provider=provider, model=model, is_active=True).first()
        if personal:
            api_key = _decrypt_user_api_key(personal.api_key_encrypted)
    else:
        active = CfgIa(tenant_id=tenant_id, provider=personal_active.provider, api_key=_decrypt_user_api_key(personal_active.api_key_encrypted), modelo=personal_active.model, max_tokens=8192, ativo=True) if personal_active else db.get(CfgIa, tenant_id)
        if not active or not active.ativo:
            raise HTTPException(400, "Nenhum provedor de IA ativo estÃ¡ configurado.")
        config = None if personal_active else db.get(CfgIaProvider, (tenant_id, active.provider))
        provider = active.provider
        api_key = (config.api_key if config else None) or active.api_key
        model = (config.modelo if config else None) or active.modelo
        system_prompt = (config.system_prompt if config else None) or active.system_prompt
        max_tokens = (config.max_tokens if config else None) or active.max_tokens or 8192
        endpoint_url = config.endpoint_url if config else None
    if api_key and model:
        _validate_model_provider(provider, model)
    if provider != "openai":
        if not api_key or not model:
            raise HTTPException(400, f"Configure a chave API e o modelo do provedor {provider}.")
        _validate_model_provider(provider, model)
        content = _provider_response(provider, api_key, model, system_prompt or "Você é um assistente jurídico especializado em direito brasileiro. Responda em português brasileiro.", messages, max_tokens, endpoint_url)
        return {"content": content}
    if provider != "openai":
        raise HTTPException(400, "O chat deste endpoint estÃ¡ configurado para modelos OpenAI.")
    if not api_key or not model:
        raise HTTPException(400, "Configure a chave API e o modelo da OpenAI.")
    content = _openai_response(api_key, model, system_prompt or "VocÃª Ã© um assistente jurÃ­dico especializado em direito brasileiro. Responda em portuguÃªs brasileiro.", messages, max_tokens, endpoint_url)
    return {"content": content}


@router.get("/k1/lex/ia/politica")
def get_effective_ai_policy(db: Session = Depends(get_db), payload=Depends(verify_token)):
    return _effective_ai_policy(db, payload)


@router.get("/k1/lex/ia/admin/politicas")
def list_ai_plan_policies(db: Session = Depends(get_db), payload=Depends(_require_admin)):
    tenant_id = payload.get("tenant_id") or payload.get("sub")
    saved = {
        row.plan_key: row
        for row in db.query(AIPlanPolicy).filter_by(tenant_id=tenant_id).all()
    }
    plans = list(AI_DEFAULT_PLANS)
    known_plans = db.execute(
        sql_text("SELECT DISTINCT plano FROM tenants WHERE plano IS NOT NULL")
    ).scalars().all()
    known_keys = {key for key, _label in plans}
    for known_plan in known_plans:
        key = str(known_plan or "").strip().lower()
        if key and key not in known_keys:
            plans.append((key, key.replace("_", " ").title()))
            known_keys.add(key)

    return [
        {
            "plan_key": key,
            "plan_label": label,
            "can_create_agents": bool(saved[key].can_create_agents) if key in saved else False,
            "allowed_roles": _ai_json_items(saved[key].allowed_roles, ["advogado"]) if key in saved else ["advogado"],
            "max_agents": saved[key].max_agents if key in saved else 0,
            "allowed_models": _ai_json_items(saved[key].allowed_models, []) if key in saved else [],
            "allowed_menus": _ai_json_items(saved[key].allowed_menus, AI_DEFAULT_MENUS) if key in saved else list(AI_DEFAULT_MENUS),
            "monthly_token_limit": saved[key].monthly_token_limit if key in saved else 0,
            "fallback_provider": saved[key].fallback_provider if key in saved else None,
            "fallback_model": saved[key].fallback_model if key in saved else None,
        }
        for key, label in plans
    ]


@router.put("/k1/lex/ia/admin/politicas/{plan_key}")
def save_ai_plan_policy(
    plan_key: str,
    body: AIPlanPolicyIn,
    db: Session = Depends(get_db),
    payload=Depends(_require_admin),
):
    tenant_id = payload.get("tenant_id") or payload.get("sub")
    plan_key = plan_key.strip().lower()
    if not re.fullmatch(r"[a-z0-9][a-z0-9_-]{0,39}", plan_key):
        raise HTTPException(400, "Identificador de plano inválido.")
    known_plan = db.execute(
        sql_text("SELECT 1 FROM tenants WHERE LOWER(plano)=:plan_key LIMIT 1"),
        {"plan_key": plan_key},
    ).scalar()
    if plan_key not in {key for key, _label in AI_DEFAULT_PLANS} and not known_plan:
        raise HTTPException(400, "Plano inválido.")
    if body.max_agents < 0 or body.monthly_token_limit < 0:
        raise HTTPException(400, "Limites não podem ser negativos.")

    row = db.query(AIPlanPolicy).filter_by(tenant_id=tenant_id, plan_key=plan_key).first()
    if not row:
        row = AIPlanPolicy(tenant_id=tenant_id, plan_key=plan_key)
        db.add(row)
    row.can_create_agents = body.can_create_agents
    row.allowed_roles = json.dumps(body.allowed_roles)
    row.max_agents = body.max_agents
    row.allowed_models = json.dumps(body.allowed_models)
    row.allowed_menus = json.dumps(body.allowed_menus)
    row.monthly_token_limit = body.monthly_token_limit
    row.fallback_provider = body.fallback_provider
    row.fallback_model = body.fallback_model
    db.commit()
    return {"plan_key": plan_key, **body.model_dump()}


@router.get("/k1/lex/ia/admin/usuarios/{user_id}")
def get_ai_user_policy(
    user_id: str,
    db: Session = Depends(get_db),
    payload=Depends(_require_admin),
):
    tenant_id = payload.get("tenant_id") or payload.get("sub")
    user_exists = db.execute(
        sql_text("SELECT 1 FROM usuarios WHERE id=:user_id AND tenant_id=:tenant_id LIMIT 1"),
        {"user_id": user_id, "tenant_id": tenant_id},
    ).scalar()
    if not user_exists:
        raise HTTPException(404, "Usuário não encontrado neste tenant.")
    row = db.query(AIUserPolicy).filter_by(tenant_id=tenant_id, user_id=user_id).first()
    if not row:
        return {
            "user_id": user_id,
            "can_create_agents": None,
            "max_agents": None,
            "monthly_token_limit": None,
            "allowed_models": None,
            "allowed_menus": None,
        }
    return {
        "user_id": user_id,
        "can_create_agents": row.can_create_agents,
        "max_agents": row.max_agents,
        "monthly_token_limit": row.monthly_token_limit,
        "allowed_models": _ai_json_items(row.allowed_models, []) if row.allowed_models is not None else None,
        "allowed_menus": _ai_json_items(row.allowed_menus, []) if row.allowed_menus is not None else None,
    }


@router.put("/k1/lex/ia/admin/usuarios/{user_id}")
def save_ai_user_policy(
    user_id: str,
    body: AIUserPolicyIn,
    db: Session = Depends(get_db),
    payload=Depends(_require_admin),
):
    tenant_id = payload.get("tenant_id") or payload.get("sub")
    user_exists = db.execute(
        sql_text("SELECT 1 FROM usuarios WHERE id=:user_id AND tenant_id=:tenant_id LIMIT 1"),
        {"user_id": user_id, "tenant_id": tenant_id},
    ).scalar()
    if not user_exists:
        raise HTTPException(404, "Usuário não encontrado neste tenant.")
    if any(value is not None and value < 0 for value in (body.max_agents, body.monthly_token_limit)):
        raise HTTPException(400, "Limites não podem ser negativos.")

    row = db.query(AIUserPolicy).filter_by(tenant_id=tenant_id, user_id=user_id).first()
    if not row:
        row = AIUserPolicy(tenant_id=tenant_id, user_id=user_id)
        db.add(row)
    values = body.model_dump(exclude_unset=True)
    for field in ("allowed_models", "allowed_menus"):
        if field in values and values[field] is not None:
            values[field] = json.dumps(values[field])
    for field, value in values.items():
        setattr(row, field, value)
    db.commit()
    return {"user_id": user_id, **body.model_dump()}
