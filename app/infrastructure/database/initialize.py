from datetime import datetime

from app.core.config import DB_HOST, DB_NAME, DB_PORT, DB_USER
from app.infrastructure.database.models import Base, Tenant
from app.infrastructure.database.session import SessionLocal, engine


def _init_db():
    try:
        print(f"[INIT] Conectando ao banco: {DB_HOST}:{DB_PORT}/{DB_NAME} (usuário: {DB_USER})")
        Base.metadata.create_all(engine)
        print("[INIT] Tabelas criadas com sucesso")
        
        with SessionLocal() as db:
            tenant = db.query(Tenant).filter_by(slug="kealex").first()
            if not tenant:
                now = datetime.utcnow()
                tenant = Tenant(
                    nome="Kealex", slug="kealex", plano="admin",
                    trial_started_at=None, trial_expires_at=None,
                )
                db.add(tenant)
                db.flush()
                print("[INIT] Tenant criado")
            else:
                # tenant admin nunca expira
                if tenant.plano == "trial" and tenant.trial_started_at is None:
                    tenant.plano = "admin"
                    db.flush()
            db.commit()
        
        print("[INIT] Banco de dados inicializado com sucesso")
    except Exception as e:
        print(f"[ERRO] Database init falhou: {type(e).__name__}: {str(e)}")
        # Os valores são importados da configuração centralizada. Mantenha a
        # mensagem de diagnóstico protegida para não mascarar a exceção original.
        try:
            print(f"[ERRO] Verifique as credenciais: {DB_USER}@{DB_HOST}:{DB_PORT}/{DB_NAME}")
        except Exception as log_error:
            print(f"[ERRO] Não foi possível exibir os dados da conexão: {log_error}")
        import traceback
        traceback.print_exc()
        raise


__all__ = ["_init_db"]
