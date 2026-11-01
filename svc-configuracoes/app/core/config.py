import base64
import hashlib
import os
from cryptography.fernet import Fernet
from dotenv import load_dotenv
from sqlalchemy.engine import URL, make_url
load_dotenv()

def _get_database_url():
    host = os.getenv("KEALEX_DB_HOST")
    database = os.getenv("KEALEX_DB_NAME")
    username = os.getenv("KEALEX_DB_USER")
    password = os.getenv("KEALEX_DB_PASSWORD")
    if host and database and username and password is not None:
        return URL.create(
            drivername="mysql+pymysql",
            username=username,
            password=password,
            host=host,
            port=int(os.getenv("KEALEX_DB_PORT", "3306")),
            database=database,
        )
    raw = os.getenv("KEALEX_DATABASE_URL")
    if raw is None or raw.strip().lower() in ("", "null", "none"):
        raise RuntimeError("Configure KEALEX_DB_HOST, KEALEX_DB_NAME, KEALEX_DB_USER e KEALEX_DB_PASSWORD (ou KEALEX_DATABASE_URL)")
    return make_url(raw.strip())

KEALEX_DATABASE_URL = _get_database_url()
KEALEX_SECRET_KEY = os.getenv("KEALEX_SECRET_KEY") or os.getenv("KEALEX_JWT_SECRET")
if not KEALEX_SECRET_KEY:
    raise RuntimeError("KEALEX_SECRET_KEY ou KEALEX_JWT_SECRET precisa estar configurada no ambiente")
_api_key_crypto_secret = os.getenv("KEALEX_API_KEYS_ENCRYPTION_KEY") or os.getenv("KEALEX_JWT_SECRET") or os.getenv("KEALEX_SECRET_KEY")
_api_key_fernet_key = _api_key_crypto_secret.encode() if os.getenv("KEALEX_API_KEYS_ENCRYPTION_KEY") else base64.urlsafe_b64encode(hashlib.sha256((_api_key_crypto_secret + ":user-api-keys:v1").encode()).digest())
try:
    API_KEY_FERNET = Fernet(_api_key_fernet_key)
except (ValueError, TypeError) as exc:
    raise RuntimeError("KEALEX_API_KEYS_ENCRYPTION_KEY precisa ser uma chave Fernet vÃ¡lida.") from exc
ALGORITHM = "HS256"

