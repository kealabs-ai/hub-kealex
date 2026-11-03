from fastapi.security import HTTPBearer
import os
from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker

from app.core.config import KEALEX_DATABASE_URL

engine = create_engine(
    KEALEX_DATABASE_URL,
    pool_pre_ping=True,
    pool_recycle=280,
    pool_size=int((os.getenv("KEALEX_DB_POOL_SIZE") or "2")),
    max_overflow=int((os.getenv("KEALEX_DB_MAX_OVERFLOW") or "1")),
    pool_timeout=int((os.getenv("KEALEX_DB_POOL_TIMEOUT") or "10")),
)
SessionLocal = sessionmaker(bind=engine, autocommit=False, autoflush=False)
bearer = HTTPBearer()

def get_db():
    db = SessionLocal()
    try:
        yield db
    except Exception:
        db.rollback()
        raise
    finally:
        db.close()


__all__ = [name for name in globals() if not name.startswith("__")]
