import os
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from app.core.config import DATABASE_URL
from app.infrastructure.database.models.activity_model import Base

engine = create_engine(
    DATABASE_URL,
    pool_pre_ping=True,
    pool_recycle=280,
    pool_size=int((os.getenv("KEALEX_DB_POOL_SIZE") or "2")),
    max_overflow=int((os.getenv("KEALEX_DB_MAX_OVERFLOW") or "1")),
    pool_timeout=int((os.getenv("KEALEX_DB_POOL_TIMEOUT") or "10")),
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
