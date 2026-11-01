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
from app.api.schemas.configuration_schema import GeralIn, CdnIn, DatabaseIn, UserApiKeyCreate, UserApiKeyUpdate, IaIn, IaProviderIn, IaChatMessage, IaChatIn, UsuariosIn, SegurancaIn, NotificacoesIn

router = APIRouter()


@router.get("/k1/lex/configuracoes/geral")
def get_geral(db: Session = Depends(get_db), payload=Depends(require_admin)):
    tenant_id = payload.get("tenant_id") or payload.get("sub")
    user_id = payload.get("sub")
    return _row(_get_or_create(db, CfgGeral, tenant_id, user_id))

@router.post("/k1/lex/configuracoes/geral")
def save_geral(body: GeralIn, db: Session = Depends(get_db), payload=Depends(require_admin)):
    tenant_id = payload.get("tenant_id") or payload.get("sub")
    user_id = payload.get("sub")
    return _row(_upsert(db, CfgGeral, tenant_id, user_id, body.model_dump(exclude_none=True)))

# â”€â”€ CDN â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€


@router.get("/k1/lex/configuracoes/cdn")
def get_cdn(db: Session = Depends(get_db), payload=Depends(require_admin)):
    tenant_id = payload.get("tenant_id") or payload.get("sub")
    user_id = payload.get("sub")
    return _row(_get_or_create(db, CfgCdn, tenant_id, user_id))

@router.post("/k1/lex/configuracoes/cdn")
def save_cdn(body: CdnIn, db: Session = Depends(get_db), payload=Depends(require_admin)):
    tenant_id = payload.get("tenant_id") or payload.get("sub")
    user_id = payload.get("sub")
    return _row(_upsert(db, CfgCdn, tenant_id, user_id, body.model_dump(exclude_none=True)))

# â”€â”€ Database â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€


@router.get("/k1/lex/configuracoes/database/env")
def get_database_env(payload=Depends(require_admin)):
    """Retorna os dados de conexÃ£o sem revelar a senha."""
    database_url = make_url(KEALEX_DATABASE_URL)
    return {
        "host": database_url.host or "",
        "port": str(database_url.port or ""),
        "name": database_url.database or "",
        "user": database_url.username or "",
        "password": "********" if database_url.password else "",
        "connection_string": database_url.render_as_string(hide_password=True),
    }

@router.get("/k1/lex/configuracoes/database")
def get_database(db: Session = Depends(get_db), payload=Depends(require_admin)):
    tenant_id = payload.get("tenant_id") or payload.get("sub")
    user_id = payload.get("sub")
    return _row(_get_or_create(db, CfgDatabase, tenant_id, user_id))

@router.post("/k1/lex/configuracoes/database")
def save_database(body: DatabaseIn, db: Session = Depends(get_db), payload=Depends(require_admin)):
    tenant_id = payload.get("tenant_id") or payload.get("sub")
    user_id = payload.get("sub")
    return _row(_upsert(db, CfgDatabase, tenant_id, user_id, body.model_dump(exclude_none=True)))

# â”€â”€ IA â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€

# Modelos disponÃ­veis por provider (lista de referÃªncia)
# Nota: O endpoint aceita modelos dinÃ¢micos nÃ£o listados aqui
from app.application.use_cases.ai_catalog import MODELOS_DISPONIVEIS, IA_DEFAULT_MODELS, _validate_model_provider
from app.application.use_cases.ai_policy import _assert_ai_menu
from app.application.use_cases.user_api_keys import (_current_api_key_owner, _decrypt_user_api_key, _encrypt_user_api_key, _user_api_key_json, _validate_user_api_key)



@router.get("/k1/lex/configuracoes/ia/minhas-chaves")
def list_my_ia_keys(db: Session = Depends(get_db), payload=Depends(verify_token)):
    user_id, tenant_id = _current_api_key_owner(payload)
    _assert_ai_menu(db, payload, "/configuracoes/ia")
    rows = db.query(UserApiKey).filter_by(user_id=user_id, tenant_id=tenant_id).order_by(UserApiKey.created_at.desc()).all()
    return [_user_api_key_json(row) for row in rows]

@router.post("/k1/lex/configuracoes/ia/minhas-chaves", status_code=201)
def create_my_ia_key(body: UserApiKeyCreate, db: Session = Depends(get_db), payload=Depends(verify_token)):
    user_id, tenant_id = _current_api_key_owner(payload)
    _assert_ai_menu(db, payload, "/configuracoes/ia")
    _validate_model_provider(body.provider, body.model)
    _validate_user_api_key(body.provider, body.api_key.strip())
    if db.query(UserApiKey).filter_by(user_id=user_id, provider=body.provider, model=body.model).first():
        raise HTTPException(409, "JÃ¡ existe uma chave cadastrada para este provedor e modelo.")
    if body.is_active:
        db.query(UserApiKey).filter_by(user_id=user_id, tenant_id=tenant_id, is_active=True).update({"is_active": False}, synchronize_session=False)
    row = UserApiKey(tenant_id=tenant_id, user_id=user_id, created_by=user_id, provider=body.provider, model=body.model, api_key_encrypted=_encrypt_user_api_key(body.api_key.strip()), is_active=body.is_active)
    db.add(row)
    db.commit()
    db.refresh(row)
    return _user_api_key_json(row)

@router.put("/k1/lex/configuracoes/ia/minhas-chaves/{key_id}")
def update_my_ia_key(key_id: str, body: UserApiKeyUpdate, db: Session = Depends(get_db), payload=Depends(verify_token)):
    user_id, tenant_id = _current_api_key_owner(payload)
    _assert_ai_menu(db, payload, "/configuracoes/ia")
    row = db.query(UserApiKey).filter_by(id=key_id, user_id=user_id, tenant_id=tenant_id).first()
    if not row:
        raise HTTPException(404, "Chave de IA nÃ£o encontrada.")
    provider, model = body.provider or row.provider, body.model or row.model
    _validate_model_provider(provider, model)
    duplicate = db.query(UserApiKey).filter(UserApiKey.user_id == user_id, UserApiKey.provider == provider, UserApiKey.model == model, UserApiKey.id != row.id).first()
    if duplicate:
        raise HTTPException(409, "JÃ¡ existe uma chave cadastrada para este provedor e modelo.")
    secret = body.api_key.strip() if body.api_key and body.api_key.strip() else _decrypt_user_api_key(row.api_key_encrypted)
    _validate_user_api_key(provider, secret)
    if body.is_active is True:
        db.query(UserApiKey).filter(UserApiKey.user_id == user_id, UserApiKey.tenant_id == tenant_id, UserApiKey.id != row.id, UserApiKey.is_active.is_(True)).update({"is_active": False}, synchronize_session=False)
    row.provider, row.model, row.api_key_encrypted = provider, model, _encrypt_user_api_key(secret)
    if body.is_active is not None: row.is_active = body.is_active
    row.updated_at = datetime.utcnow()
    db.commit()
    db.refresh(row)
    return _user_api_key_json(row)

@router.delete("/k1/lex/configuracoes/ia/minhas-chaves/{key_id}", status_code=204)
def delete_my_ia_key(key_id: str, db: Session = Depends(get_db), payload=Depends(verify_token)):
    user_id, tenant_id = _current_api_key_owner(payload)
    _assert_ai_menu(db, payload, "/configuracoes/ia")
    row = db.query(UserApiKey).filter_by(id=key_id, user_id=user_id, tenant_id=tenant_id).first()
    if not row:
        raise HTTPException(404, "Chave de IA nÃ£o encontrada.")
    db.delete(row)
    db.commit()


@router.get("/k1/lex/configuracoes/ia")
def get_ia(db: Session = Depends(get_db), payload=Depends(require_admin)):
    tenant_id = payload.get("tenant_id") or payload.get("sub")
    user_id = payload.get("sub")
    active = _get_or_create(db, CfgIa, tenant_id, user_id)
    provider_cfg = db.get(CfgIaProvider, (tenant_id, active.provider))
    result = _row(active)
    result.pop("api_key", None)
    result["configured"] = bool((provider_cfg.api_key if provider_cfg else None) or active.api_key)
    return result

@router.get("/k1/lex/configuracoes/ia/modelos")
def get_modelos_disponiveis():
    """Retorna a lista de modelos disponÃ­veis por provider (referÃªncia apenas)
    Nota: O endpoint POST /k1/lex/configuracoes/ia aceita qualquer modelo, nÃ£o apenas os listados aqui
    """
    return MODELOS_DISPONIVEIS

@router.get("/k1/lex/configuracoes/ia/ativa")
def get_ia_ativa(db: Session = Depends(get_db), payload=Depends(verify_token)):
    """Retorna a configuraÃ§Ã£o de IA ativa para o tenant (nÃ£o requer admin)"""
    tenant_id = payload.get("tenant_id") or payload.get("sub")
    user_id = payload.get("sub")
    active = _get_or_create(db, CfgIa, tenant_id, user_id)
    provider_cfg = db.get(CfgIaProvider, (tenant_id, active.provider))
    result = _row(active)
    result.pop("api_key", None)
    result["configured"] = bool((provider_cfg.api_key if provider_cfg else None) or active.api_key)
    return result

@router.post("/k1/lex/configuracoes/ia")
def save_ia(body: IaIn, db: Session = Depends(get_db), payload=Depends(require_admin)):
    data = body.model_dump(exclude_none=True)
    
    tenant_id = payload.get("tenant_id") or payload.get("sub")
    current = db.get(CfgIa, tenant_id)
    if "provider" in data or "modelo" in data:
        _validate_model_provider(data.get("provider") or (current.provider if current else "cerebras"), data.get("modelo") or (current.modelo if current else IA_DEFAULT_MODELS["cerebras"]))
    
    # Permitir qualquer modelo (sem validaÃ§Ã£o restrita Ã  lista)
    # O frontend pode enviar modelos dinÃ¢micos nÃ£o listados em MODELOS_DISPONIVEIS
    
    # Validar prefixo da API key
    if "api_key" in data and data["api_key"]:
        tenant_id = payload.get("tenant_id") or payload.get("sub")
        existing = db.get(CfgIa, tenant_id)
        provider = data.get("provider") or (existing.provider if existing else "cerebras")
        if provider == "cerebras" and not data["api_key"].startswith("csk-"):
            raise HTTPException(400, "API key Cerebras deve comeÃ§ar com 'csk-'")
        if provider == "groq" and not (data["api_key"].startswith("gsk-") or data["api_key"].startswith("gsk_")):
            raise HTTPException(400, "API key Groq deve comeÃ§ar com 'gsk-' ou 'gsk_'")
    
    tenant_id = payload.get("tenant_id") or payload.get("sub")
    user_id = payload.get("sub")
    return _row(_upsert(db, CfgIa, tenant_id, user_id, data))


@router.get("/k1/lex/configuracoes/ia/provedores")
def get_ia_provedores(db: Session = Depends(get_db), payload=Depends(require_admin)):
    tenant_id = payload.get("tenant_id") or payload.get("sub")
    user_id = payload.get("sub")
    active = _get_or_create(db, CfgIa, tenant_id, user_id)
    rows = db.query(CfgIaProvider).filter_by(tenant_id=tenant_id).all()
    configs = {}
    for row in rows:
        item = _row(row)
        item["configured"] = bool(item.pop("api_key", None))
        configs[row.provider] = item
    # Compatibilidade: migra a configuraÃ§Ã£o antiga para a respectiva aba na primeira leitura.
    if active.provider not in configs:
        legacy = CfgIaProvider(
            tenant_id=tenant_id, user_id=user_id, provider=active.provider,
            api_key=active.api_key, modelo=active.modelo or IA_DEFAULT_MODELS.get(active.provider, ""),
            max_tokens=active.max_tokens or 8192, system_prompt=active.system_prompt, ativo=active.ativo,
        )
        db.add(legacy)
        db.commit()
        db.refresh(legacy)
        item = _row(legacy)
        item["configured"] = bool(item.pop("api_key", None))
        configs[legacy.provider] = item
    return {"active_provider": active.provider, "providers": configs}

@router.post("/k1/lex/configuracoes/ia/provedores/{provider}")
def save_ia_provedor(provider: str, body: IaProviderIn, db: Session = Depends(get_db), payload=Depends(require_admin)):
    if provider not in MODELOS_DISPONIVEIS:
        raise HTTPException(400, "Provider invÃ¡lido")
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
        row = CfgIaProvider(tenant_id=tenant_id, provider=provider, user_id=user_id,
                            modelo=IA_DEFAULT_MODELS[provider])
        db.add(row)
    for key, value in data.items():
        setattr(row, key, value)
    row.updated_at = datetime.utcnow()
    active = db.get(CfgIa, tenant_id)
    if active and active.provider == provider:
        active.api_key = row.api_key
        active.modelo = row.modelo
        active.max_tokens = row.max_tokens
        active.system_prompt = row.system_prompt
        active.ativo = row.ativo
        active.updated_at = datetime.utcnow()
    db.commit()
    db.refresh(row)
    result = _row(row)
    result["configured"] = bool(result.pop("api_key", None))
    return result

@router.post("/k1/lex/configuracoes/ia/provedor-ativo/{provider}")
def set_ia_provedor_ativo(provider: str, db: Session = Depends(get_db), payload=Depends(require_admin)):
    if provider not in MODELOS_DISPONIVEIS:
        raise HTTPException(400, "Provider invÃ¡lido")
    tenant_id = payload.get("tenant_id") or payload.get("sub")
    user_id = payload.get("sub")
    provider_cfg = db.get(CfgIaProvider, (tenant_id, provider))
    if provider_cfg is None or not provider_cfg.api_key:
        raise HTTPException(400, "Configure a chave API deste provedor antes de ativÃ¡-lo")
    if not provider_cfg.ativo:
        raise HTTPException(400, "Habilite este provedor antes de ativÃ¡-lo")
    active = _get_or_create(db, CfgIa, tenant_id, user_id)
    active.provider = provider
    active.api_key = provider_cfg.api_key
    active.modelo = provider_cfg.modelo
    active.max_tokens = provider_cfg.max_tokens
    active.system_prompt = provider_cfg.system_prompt
    active.ativo = provider_cfg.ativo
    active.updated_at = datetime.utcnow()
    db.commit()
    result = _row(active)
    result.pop("api_key", None)
    result["configured"] = True
    return result

# â”€â”€ UsuÃ¡rios â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€



def _openai_response(api_key: str, model: str, system_prompt: str, messages: list[dict], max_tokens: int, endpoint_url: Optional[str]) -> str:
    base = (endpoint_url or "https://api.openai.com/v1").rstrip("/")
    if base != "https://api.openai.com/v1":
        raise HTTPException(400, "Use o endpoint oficial https://api.openai.com/v1 da OpenAI.")
    request = urllib.request.Request(
        f"{base}/responses",
        data=json.dumps({"model": model, "instructions": system_prompt, "input": messages, "max_output_tokens": max_tokens}).encode("utf-8"),
        headers={"Authorization": f"Bearer {api_key}", "Content-Type": "application/json"},
        method="POST",
    )
    try:
        with urllib.request.urlopen(request, timeout=120) as response:
            result = json.loads(response.read().decode("utf-8"))
    except urllib.error.HTTPError as exc:
        detail = exc.read().decode("utf-8", errors="replace")
        raise HTTPException(502, f"A OpenAI respondeu com erro ({exc.code}): {detail[:1000]}") from exc
    except (urllib.error.URLError, TimeoutError) as exc:
        raise HTTPException(502, "NÃƒÂ£o foi possÃƒÂ­vel conectar ÃƒÂ  OpenAI.") from exc
    return result.get("output_text") or "".join(
        part.get("text", "") for item in result.get("output", [])
        for part in item.get("content", []) if part.get("type") == "output_text"
    )

def _provider_response(provider: str, api_key: str, model: str, system_prompt: str, messages: list[dict], max_tokens: int, endpoint_url: Optional[str] = None) -> str:
    if provider == "openai":
        return _openai_response(api_key, model, system_prompt, messages, max_tokens, endpoint_url)
    if provider == "claude":
        url = "https://api.anthropic.com/v1/messages"
        headers = {"x-api-key": api_key, "anthropic-version": "2023-06-01"}
        data = {"model": model, "max_tokens": max_tokens, "system": system_prompt, "messages": messages}
    elif provider == "google":
        url = f"https://generativelanguage.googleapis.com/v1beta/models/{model}:generateContent?key={api_key}"
        headers = {}
        data = {"systemInstruction": {"parts": [{"text": system_prompt}]}, "contents": [{"role": "model" if m["role"] == "assistant" else "user", "parts": [{"text": m["content"]}]} for m in messages], "generationConfig": {"maxOutputTokens": max_tokens}}
    else:
        base = {"groq": "https://api.groq.com/openai/v1", "cerebras": "https://api.cerebras.ai/v1", "deepseek": "https://api.deepseek.com"}.get(provider)
        if not base:
            raise HTTPException(400, "Fabricante de IA nÃ£o suportado.")
        url, headers = f"{base}/chat/completions", {"Authorization": f"Bearer {api_key}"}
        data = {"model": model, "messages": [{"role": "system", "content": system_prompt}, *messages], "max_tokens": max_tokens}
    headers.update({"Content-Type": "application/json", "Accept": "application/json", "User-Agent": "Kealex-AI/1.0"})
    request = urllib.request.Request(url, data=json.dumps(data).encode("utf-8"), headers=headers, method="POST")
    try:
        with urllib.request.urlopen(request, timeout=120) as response:
            result = json.loads(response.read().decode("utf-8"))
    except urllib.error.HTTPError as exc:
        detail = exc.read().decode("utf-8", errors="replace")
        if provider == "groq" and exc.code == 403 and "1010" in detail:
            raise HTTPException(502, "O acesso do servidor ao Groq foi bloqueado pelo Cloudflare (erro 1010). Confira as regras de seguranÃ§a ou a rota de saÃ­da do servidor no provedor.") from exc
        raise HTTPException(502, f"{provider} respondeu com erro ({exc.code}): {detail[:1000]}") from exc
    except (urllib.error.URLError, TimeoutError) as exc:
        raise HTTPException(502, f"NÃ£o foi possÃ­vel conectar ao provedor {provider}.") from exc
    if provider == "claude":
        return "".join(part.get("text", "") for part in result.get("content", []))
    if provider == "google":
        return "".join(part.get("text", "") for part in result.get("candidates", [{}])[0].get("content", {}).get("parts", []))
    return result.get("choices", [{}])[0].get("message", {}).get("content", "")

def _record_ai_usage(db: Session, tenant_id: str, user_id: str, messages: list, answer: str):
    # Approximation for providers whose wrapper does not expose usage metadata.
    used = max(1, (sum(len(str(item.get("content", ""))) for item in messages) + len(answer or "")) // 4)
    period = datetime.utcnow().strftime("%Y-%m")
    row = db.query(AITokenUsage).filter_by(tenant_id=tenant_id, user_id=user_id, period=period).first()
    if row:
        row.tokens_used += used
    else:
        db.add(AITokenUsage(tenant_id=tenant_id, user_id=user_id, period=period, tokens_used=used))
    db.commit()

@router.post("/k1/lex/configuracoes/ia/chat")
def chat_ia(body: IaChatIn, db: Session = Depends(get_db), payload=Depends(verify_token)):
    user_id, tenant_id = _current_api_key_owner(payload)
    _assert_ai_menu(db, payload, "/ia")
    personal_active = db.query(UserApiKey).filter_by(user_id=user_id, tenant_id=tenant_id, is_active=True).first()
    messages = [{"role": m.role, "content": m.content[:32000]} for m in body.messages[-50:] if m.role in ("user", "assistant")]
    if not messages or messages[-1]["role"] != "user":
        raise HTTPException(400, "A ÃƒÂºltima mensagem deve ser do usuÃƒÂ¡rio.")
    if body.agente_id:
        config = db.query(AgenteIA).filter(AgenteIA.id == body.agente_id, AgenteIA.tenant_id == tenant_id, AgenteIA.ativo == True, ((AgenteIA.publico == True) | (AgenteIA.owner_user_id == user_id))).first()
        if not config:
            raise HTTPException(404, "Agente de IA nÃƒÂ£o encontrado.")
        provider, api_key, model = config.provider, config.api_key, config.modelo
        system_prompt, max_tokens, endpoint_url = config.system_prompt, config.max_tokens or 8192, None
        personal = db.query(UserApiKey).filter_by(user_id=user_id, tenant_id=tenant_id, provider=provider, model=model, is_active=True).first()
        if personal:
            api_key = _decrypt_user_api_key(personal.api_key_encrypted)
    else:
        active = CfgIa(tenant_id=tenant_id, provider=personal_active.provider, api_key=_decrypt_user_api_key(personal_active.api_key_encrypted), modelo=personal_active.model, max_tokens=8192, ativo=True) if personal_active else db.get(CfgIa, tenant_id)
        if not active or not active.ativo:
            raise HTTPException(400, "Nenhum provedor de IA ativo estÃƒÂ¡ configurado.")
        config = None if personal_active else db.get(CfgIaProvider, (tenant_id, active.provider))
        provider = active.provider
        api_key = (config.api_key if config else None) or active.api_key
        model = (config.modelo if config else None) or active.modelo
        system_prompt = (config.system_prompt if config else None) or active.system_prompt
        max_tokens = (config.max_tokens if config else None) or active.max_tokens or 8192
        endpoint_url = config.endpoint_url if config else None
    policy = _effective_ai_policy(db, payload)
    if not _model_allowed(policy, provider, model):
        raise HTTPException(403, "O modelo selecionado nÃ£o estÃ¡ liberado no seu plano.")
    if policy["monthly_token_limit"] > 0 and policy["tokens_used"] >= policy["monthly_token_limit"]:
        fallback_provider, fallback_model = policy.get("fallback_provider"), policy.get("fallback_model")
        fallback_key = db.query(UserApiKey).filter_by(user_id=user_id, tenant_id=tenant_id, provider=fallback_provider, model=fallback_model, is_active=True).first() if fallback_provider and fallback_model else None
        if not fallback_key:
            raise HTTPException(429, "A cota mensal de tokens terminou e nÃ£o hÃ¡ chave pessoal para o modelo de continuidade do plano.")
        provider, model = fallback_provider, fallback_model
        api_key = _decrypt_user_api_key(fallback_key.api_key_encrypted)
        endpoint_url = None
    if api_key and model:
        _validate_model_provider(provider, model)
    if not api_key or not model:
        raise HTTPException(400, f"Configure a chave API e o modelo do provedor {provider}.")
    _validate_model_provider(provider, model)
    system = system_prompt or "Você é um assistente jurídico especializado em direito brasileiro. Responda em português brasileiro."
    if provider == "openai":
        content = _openai_response(api_key, model, system, messages, max_tokens, endpoint_url)
    else:
        content = _provider_response(provider, api_key, model, system, messages, max_tokens, endpoint_url)
    _record_ai_usage(db, tenant_id, user_id, messages, content)
    return {"content": content, "provider": provider, "model": model}

@router.get("/k1/lex/configuracoes/usuarios")
def get_usuarios(db: Session = Depends(get_db), payload=Depends(require_admin)):
    tenant_id = payload.get("tenant_id") or payload.get("sub")
    user_id = payload.get("sub")
    return _row(_get_or_create(db, CfgUsuarios, tenant_id, user_id))

@router.post("/k1/lex/configuracoes/usuarios")
def save_usuarios(body: UsuariosIn, db: Session = Depends(get_db), payload=Depends(require_admin)):
    tenant_id = payload.get("tenant_id") or payload.get("sub")
    user_id = payload.get("sub")
    return _row(_upsert(db, CfgUsuarios, tenant_id, user_id, body.model_dump(exclude_none=True)))

# â”€â”€ SeguranÃ§a â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€


@router.get("/k1/lex/configuracoes/seguranca")
def get_seguranca(db: Session = Depends(get_db), payload=Depends(require_admin)):
    tenant_id = payload.get("tenant_id") or payload.get("sub")
    user_id = payload.get("sub")
    return _row(_get_or_create(db, CfgSeguranca, tenant_id, user_id))

@router.post("/k1/lex/configuracoes/seguranca")
def save_seguranca(body: SegurancaIn, db: Session = Depends(get_db), payload=Depends(require_admin)):
    tenant_id = payload.get("tenant_id") or payload.get("sub")
    user_id = payload.get("sub")
    return _row(_upsert(db, CfgSeguranca, tenant_id, user_id, body.model_dump(exclude_none=True)))

# â”€â”€ NotificaÃ§Ãµes â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€


@router.get("/k1/lex/configuracoes/notificacoes")
def get_notificacoes(db: Session = Depends(get_db), payload=Depends(require_admin)):
    tenant_id = payload.get("tenant_id") or payload.get("sub")
    user_id = payload.get("sub")
    return _row(_get_or_create(db, CfgNotificacoes, tenant_id, user_id))

@router.post("/k1/lex/configuracoes/notificacoes")
def save_notificacoes(body: NotificacoesIn, db: Session = Depends(get_db), payload=Depends(require_admin)):
    tenant_id = payload.get("tenant_id") or payload.get("sub")
    user_id = payload.get("sub")
    return _row(_upsert(db, CfgNotificacoes, tenant_id, user_id, body.model_dump(exclude_none=True)))

# â”€â”€ Agentes IA â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€

