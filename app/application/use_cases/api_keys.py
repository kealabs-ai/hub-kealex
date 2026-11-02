from cryptography.fernet import InvalidToken
from fastapi import HTTPException
from sqlalchemy.orm import Session

from app.api.schemas.schemas import ChavePublicaIn
from app.core.config import API_KEY_FERNET
from app.infrastructure.database.models import Usuario


def _encrypt_user_api_key(value: str) -> str:
    return API_KEY_FERNET.encrypt(value.encode("utf-8")).decode("ascii")

def _decrypt_user_api_key(value: str) -> str:
    try:
        return API_KEY_FERNET.decrypt(value.encode("ascii")).decode("utf-8")
    except (InvalidToken, ValueError, UnicodeDecodeError) as exc:
        raise HTTPException(500, "Não foi possível descriptografar uma chave de IA. Configure a mesma chave de criptografia usada ao salvar credenciais.") from exc

def _validate_user_api_key(provider: str, value: str):
    prefixes = {"cerebras": ("csk-",), "groq": ("gsk-", "gsk_"), "openai": ("sk-",), "google": ("AIza",), "claude": ("sk-ant-",), "deepseek": ("sk-",)}
    if provider not in prefixes or not value.startswith(prefixes[provider]):
        raise HTTPException(400, f"A chave API informada não corresponde ao provedor '{provider}'.")

def _current_api_key_owner(db: Session, payload: dict) -> tuple[str, str]:
    user_id = str(payload.get("sub") or "")
    user = db.get(Usuario, user_id) if user_id else None
    if not user or not user.ativo:
        raise HTTPException(401, "Usuário autenticado não encontrado ou inativo.")
    return user.id, user.tenant_id

def _validated_public_key(body: ChavePublicaIn) -> tuple[str, str]:
    orgao = body.orgao.strip()
    chave_publica = body.chavePublica.strip()
    if not orgao or len(orgao) > 120:
        raise HTTPException(422, "Informe um órgão válido (até 120 caracteres).")
    if not chave_publica or len(chave_publica) > 10000:
        raise HTTPException(422, "Informe uma chave pública válida (até 10.000 caracteres).")
    return orgao, chave_publica

__all__ = ["_encrypt_user_api_key", "_decrypt_user_api_key", "_validate_user_api_key", "_current_api_key_owner", "_validated_public_key"]
