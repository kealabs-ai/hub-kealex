import base64
import hashlib
import os
from urllib.parse import quote_plus

from cryptography.fernet import Fernet
from dotenv import load_dotenv
from sqlalchemy.engine import make_url

load_dotenv()

def _get_database_url():
    """Monta a URL com credenciais separadas para escapar caracteres especiais."""
    host = os.getenv("KEALEX_DB_HOST")
    database = os.getenv("KEALEX_DB_NAME")
    username = os.getenv("KEALEX_DB_USER")
    password = os.getenv("KEALEX_DB_PASSWORD")

    if host and database and username and password is not None:
        # Escapar caracteres especiais na senha e username usando quote_plus
        escaped_password = quote_plus(password)
        escaped_username = quote_plus(username)
        return make_url(
            f"mysql+pymysql://{escaped_username}:{escaped_password}@"
            f"{host}:{os.getenv('KEALEX_DB_PORT', '3306')}/{database}"
        )

    legacy_url = os.getenv("KEALEX_DATABASE_URL")
    if legacy_url:
        return make_url(legacy_url)
    raise RuntimeError(
        "Configure KEALEX_DB_HOST, KEALEX_DB_NAME, KEALEX_DB_USER e KEALEX_DB_PASSWORD "
        "(ou KEALEX_DATABASE_URL para compatibilidade)"
    )

KEALEX_DATABASE_URL = _get_database_url()
DATABASE_CONFIG = make_url(KEALEX_DATABASE_URL)
DB_HOST = DATABASE_CONFIG.host or ""
DB_PORT = str(DATABASE_CONFIG.port or "")
DB_NAME = DATABASE_CONFIG.database or ""
DB_USER = DATABASE_CONFIG.username or ""

# Configurações de Autenticação
KEALEX_SECRET_KEY = os.getenv("KEALEX_JWT_SECRET") or os.getenv("KEALEX_SECRET_KEY")
if not KEALEX_SECRET_KEY:
    raise RuntimeError("KEALEX_JWT_SECRET ou KEALEX_SECRET_KEY precisa estar configurada no ambiente")
_api_key_crypto_secret = os.getenv("KEALEX_API_KEYS_ENCRYPTION_KEY") or os.getenv("KEALEX_JWT_SECRET") or os.getenv("KEALEX_SECRET_KEY")
_api_key_fernet_key = _api_key_crypto_secret.encode() if os.getenv("KEALEX_API_KEYS_ENCRYPTION_KEY") else base64.urlsafe_b64encode(hashlib.sha256((_api_key_crypto_secret + ":user-api-keys:v1").encode()).digest())
try:
    API_KEY_FERNET = Fernet(_api_key_fernet_key)
except (ValueError, TypeError) as exc:
    raise RuntimeError("KEALEX_API_KEYS_ENCRYPTION_KEY precisa ser uma chave Fernet válida.") from exc
ALGORITHM = "HS256"
KEALEX_JWT_EXPIRY_HOURS = int(os.getenv("KEALEX_JWT_EXPIRY_HOURS", "8"))
TOKEN_EXPIRE_MINUTES = KEALEX_JWT_EXPIRY_HOURS * 60

# Configurações de LLM API Keys
KEALEX_GEMINI_API_KEY = os.getenv("KEALEX_GEMINI_API_KEY", "")
KEALEX_OPENAI_API_KEY = os.getenv("KEALEX_OPENAI_API_KEY", "")
KEALEX_GROQ_API_KEY = os.getenv("KEALEX_GROQ_API_KEY", "")
KEALEX_ANTHROPIC_API_KEY = os.getenv("KEALEX_ANTHROPIC_API_KEY", "")
KEALEX_CEREBRAS_API_KEY = os.getenv("KEALEX_CEREBRAS_API_KEY", "")

# Configurações de Aplicação
KEALEX_ENVIRONMENT = os.getenv("KEALEX_ENVIRONMENT", "development")
KEALEX_DEBUG = os.getenv("KEALEX_DEBUG", "true").lower() == "true"

KEALEX_ASAAS_API_KEY = os.getenv("KEALEX_ASAAS_API_KEY", "")
ASAAS_BASE = os.getenv("KEALEX_ASAAS_BASE_URL", "").rstrip("/")
KEALEX_ASAAS_WEBHOOK_TOKEN = os.getenv("KEALEX_ASAAS_WEBHOOK_TOKEN", "")

__all__ = [name for name in globals() if not name.startswith("__")]
