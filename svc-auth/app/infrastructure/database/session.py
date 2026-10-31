from datetime import datetime, timedelta
from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker
from app.core.config import KEALEX_DATABASE_URL, TRIAL_DAYS
from app.infrastructure.database.models.auth_models import Base, Tenant, Usuario, RoleEnum
from app.infrastructure.security.bcrypt_hasher import hash_password

engine = create_engine(KEALEX_DATABASE_URL, pool_pre_ping=True, pool_recycle=280, pool_size=5, max_overflow=10)
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

            admin = db.query(Usuario).filter_by(email="admin@kealex.com").first()
            if not admin:
                admin = Usuario(
                    tenant_id=tenant.id, nome="Admin Kealex",
                    email="admin@kealex.com", senha_hash=hash_password("admin123"),
                    role=RoleEnum.admin,
                )
                db.add(admin)
            else:
                if not admin.tenant_id:
                    admin.tenant_id = tenant.id
                if not admin.senha_hash.startswith("$2b$"):
                    admin.senha_hash = hash_password("admin123")
            db.commit()
    except Exception as e:
        print(f"[ERRO] Database init falhou: {type(e).__name__}: {e}")
        import traceback; traceback.print_exc()
        raise