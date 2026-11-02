from fastapi import APIRouter

from app.legacy_context import DB_HOST, DB_NAME, DB_PORT, DB_USER, SessionLocal

router = APIRouter()


@router.get("/health")
def health_simple():
    return {"status": "healthy", "service": "hubkealex"}


@router.get("/debug/db-status")
def debug_db_status():
    """Debug endpoint para verificar status de conexão com banco de dados"""
    try:
        with SessionLocal() as db:
            result = db.execute("SELECT 1").fetchone()
        return {
            "status": "connected",
            "database_url": f"mysql+pymysql://{DB_USER}@{DB_HOST}:{DB_PORT}/{DB_NAME}",
            "host": DB_HOST,
            "port": DB_PORT,
            "database": DB_NAME
        }
    except Exception as e:
        return {
            "status": "error",
            "error": str(e),
            "database_url": f"mysql+pymysql://{DB_USER}@{DB_HOST}:{DB_PORT}/{DB_NAME}",
            "host": DB_HOST,
            "port": DB_PORT,
            "database": DB_NAME
        }


@router.get("/k1/lex/health")
def health():
    return {"status": "ok", "service": "hubkealex"}
