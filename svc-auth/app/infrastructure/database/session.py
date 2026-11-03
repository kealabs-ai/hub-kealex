import os
from datetime import datetime, timedelta
from sqlalchemy import create_engine, event
from sqlalchemy.orm import Session, sessionmaker
from app.core.config import KEALEX_DATABASE_URL, TRIAL_DAYS
from app.infrastructure.database.models.auth_models import Base, Tenant
from prometheus_client import Gauge

engine = create_engine(KEALEX_DATABASE_URL, pool_pre_ping=True, pool_recycle=280,
                       pool_size=int((os.getenv("KEALEX_DB_POOL_SIZE") or "2")),
                       max_overflow=int((os.getenv("KEALEX_DB_MAX_OVERFLOW") or "1")),
                       pool_timeout=int((os.getenv("KEALEX_DB_POOL_TIMEOUT") or "10")))
SessionLocal = sessionmaker(bind=engine, autocommit=False, autoflush=False)
DB_POOL_CHECKED_OUT = Gauge("kealex_auth_db_pool_checked_out", "Checked out SQLAlchemy connections in svc-auth")
event.listen(engine.pool, "checkout", lambda *args: DB_POOL_CHECKED_OUT.inc())
event.listen(engine.pool, "checkin", lambda *args: DB_POOL_CHECKED_OUT.dec())

def get_db():
    db = SessionLocal()
    try:
        yield db
    except Exception:
        db.rollback()
        raise
    finally:
        db.close()

def _init_db():
    try:
        Base.metadata.create_all(engine)
        with SessionLocal() as db:
            tenant = db.query(Tenant).filter_by(slug="kealex").first()
            if not tenant:
                now = datetime.utcnow()
                tenant = Tenant(
                    nome="Kealex", slug="kealex", plano="trial",
                    trial_started_at=now,
                    trial_expires_at=now + timedelta(days=TRIAL_DAYS),
                )
                db.add(tenant)
                db.flush()
            else:
                # garante que tenants antigos tenham trial_started_at preenchido
                if tenant.trial_started_at is None and tenant.plano == "trial":
                    tenant.trial_started_at = tenant.created_at
                    tenant.trial_expires_at = tenant.created_at + timedelta(days=TRIAL_DAYS)
                    db.flush()

            db.commit()
    except Exception as e:
        print(f"[ERRO] Database init falhou: {type(e).__name__}: {e}")
        import traceback; traceback.print_exc()
        raise
