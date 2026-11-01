from fastapi import HTTPException
from cryptography.fernet import InvalidToken
from app.core.config import API_KEY_FERNET
from app.infrastructure.database.models.configuration_model import UserApiKey

def _encrypt_user_api_key(value: str) -> str:
    return API_KEY_FERNET.encrypt(value.encode("utf-8")).decode("ascii")

def _decrypt_user_api_key(value: str) -> str:
    try:
        return API_KEY_FERNET.decrypt(value.encode("ascii")).decode("utf-8")
    except (InvalidToken, ValueError, UnicodeDecodeError) as exc:
        raise HTTPException(500, "NÃ£o foi possÃ­vel descriptografar uma chave de IA. Confira a chave de criptografia do serviÃ§o.") from exc

def _user_api_key_json(row: UserApiKey) -> dict:
    secret = _decrypt_user_api_key(row.api_key_encrypted)
    return {"id": row.id, "provider": row.provider, "model": row.model, "api_key_masked": "â€¢" * max(4, min(12, len(secret) - 4)) + secret[-4:], "is_active": row.is_active, "created_at": row.created_at.isoformat() if row.created_at else None, "updated_at": row.updated_at.isoformat() if row.updated_at else None}

def _validate_user_api_key(provider: str, value: str):
    prefixes = {"cerebras": ("csk-",), "groq": ("gsk-", "gsk_"), "openai": ("sk-",), "google": ("AIza",), "claude": ("sk-ant-",), "deepseek": ("sk-",)}
    if provider not in prefixes or not value.startswith(prefixes[provider]):
        raise HTTPException(400, f"A chave API informada nÃ£o corresponde ao provedor '{provider}'.")

def _current_api_key_owner(payload: dict) -> tuple[str, str]:
    user_id = str(payload.get("sub") or "")
    tenant_id = str(payload.get("tenant_id") or "")
    if not user_id or not tenant_id:
        raise HTTPException(401, "O token nÃ£o identifica o usuÃ¡rio e o tenant.")
    return user_id, tenant_id

