import os
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from app.core.config import KEALEX_DATABASE_URL
from app.infrastructure.database.models.user_model import Base

engine = create_engine(KEALEX_DATABASE_URL, pool_pre_ping=True, pool_recycle=280, pool_size=int(os.getenv("KEALEX_DB_POOL_SIZE", "3")), max_overflow=int(os.getenv("KEALEX_DB_MAX_OVERFLOW", "2")), pool_timeout=int(os.getenv("KEALEX_DB_POOL_TIMEOUT", "10")))
SessionLocal = sessionmaker(bind=engine, autocommit=False, autoflush=False)

def get_db():
    db = SessionLocal()
    try:
        yield db
    except Exception:
        try:
            db.rollback()
        except Exception:
            # Preserve the request error if the database connection was already dropped.
            pass
        raise
    finally:
        db.close()
