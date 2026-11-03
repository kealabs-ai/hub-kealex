import os

from sqlalchemy import create_engine
from sqlalchemy.engine import URL, make_url
from sqlalchemy.orm import sessionmaker


def _database_url():
    raw_url = os.getenv("KEALEX_DATABASE_URL", "").strip()
    if raw_url:
        return make_url(raw_url)

    required = (
        os.getenv("KEALEX_DB_HOST"),
        os.getenv("KEALEX_DB_NAME"),
        os.getenv("KEALEX_DB_USER"),
    )
    password = os.getenv("KEALEX_DB_PASSWORD")
    if not all(required) or password is None:
        raise RuntimeError("Configure KEALEX_DB_* ou KEALEX_DATABASE_URL")

    return URL.create(
        "mysql+pymysql",
        username=required[2],
        password=password,
        host=required[0],
        port=int(os.getenv("KEALEX_DB_PORT", "3306")),
        database=required[1],
    )


engine = create_engine(
    _database_url(),
    pool_pre_ping=True,
    pool_recycle=280,
    pool_size=int(os.getenv("KEALEX_DB_POOL_SIZE") or "2"),
    max_overflow=int(os.getenv("KEALEX_DB_MAX_OVERFLOW") or "1"),
    pool_timeout=int(os.getenv("KEALEX_DB_POOL_TIMEOUT") or "10"),
)
SessionLocal = sessionmaker(bind=engine, autocommit=False, autoflush=False)


def get_db():
    db = SessionLocal()
    try:
        yield db
    except Exception:
        db.rollback()
        raise
    finally:
        db.close()
