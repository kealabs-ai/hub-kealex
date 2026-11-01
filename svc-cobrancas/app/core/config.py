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
    if raw is None or raw.strip().lower() in ("", "null", "none"):
        raise RuntimeError(
            "Configure KEALEX_DB_HOST, KEALEX_DB_NAME, KEALEX_DB_USER e "
            "KEALEX_DB_PASSWORD (ou KEALEX_DATABASE_URL)"
        )
    return make_url(raw.strip())


DATABASE_URL = get_database_url()
SECRET_KEY = os.getenv("KEALEX_SECRET_KEY") or os.getenv("KEALEX_JWT_SECRET")
if not SECRET_KEY:
    raise RuntimeError("KEALEX_SECRET_KEY ou KEALEX_JWT_SECRET precisa estar configurada no ambiente")

ALGORITHM = "HS256"
ASAAS_API_KEY = os.getenv("KEALEX_ASAAS_API_KEY", "")
ASAAS_BASE = os.getenv(
    "KEALEX_ASAAS_BASE_URL", "https://api-sandbox.asaas.com/v3"
).rstrip("/")
ASAAS_WEBHOOK_TOKEN = os.getenv("KEALEX_ASAAS_WEBHOOK_TOKEN", "")
PREFIX = "/cobrancas"
