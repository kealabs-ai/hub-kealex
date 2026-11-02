from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from app.core.config import KEALEX_DATABASE_URL

engine = create_engine(
    KEALEX_DATABASE_URL,
    pool_pre_ping=True,
    pool_recycle=280,
    pool_size=5,
    max_overflow=10,
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
