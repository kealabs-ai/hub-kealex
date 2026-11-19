import os

from dotenv import load_dotenv
from sqlalchemy.engine import URL, make_url

load_dotenv()


def get_database_url():
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
    if not raw or raw.strip().lower() in {"null", "none"}:
        raise RuntimeError("Configure KEALEX_DB_HOST, KEALEX_DB_NAME, KEALEX_DB_USER e KEALEX_DB_PASSWORD (ou KEALEX_DATABASE_URL)")
    return make_url(raw.strip())


KEALEX_DATABASE_URL = get_database_url()
KEALEX_SECRET_KEY = os.getenv("KEALEX_SECRET_KEY") or os.getenv("KEALEX_JWT_SECRET")
if not KEALEX_SECRET_KEY:
    raise RuntimeError("KEALEX_SECRET_KEY ou KEALEX_JWT_SECRET precisa estar configurada no ambiente")
ALGORITHM = "HS256"
FISCALAPI_BASE_URL = os.getenv("FISCALAPI_BASE_URL", "https://api.fiscalapi.com.br").rstrip("/")
FISCALAPI_API_KEY = os.getenv("FISCALAPI_API_KEY", "").strip()
FISCALAPI_TIMEOUT = os.getenv("FISCALAPI_TIMEOUT", "75")
FISCALAPI_ENABLED = os.getenv("FISCALAPI_ENABLED", "false").strip().lower() in {"1", "true", "yes", "on"}
FISCALAPI_RATE_LIMIT_PER_MINUTE = max(0, int(os.getenv("FISCALAPI_RATE_LIMIT_PER_MINUTE", "30")))
