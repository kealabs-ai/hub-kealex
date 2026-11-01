from sqlalchemy import text
from sqlalchemy.orm import Session

def _usage_for_escritorio(db: Session, escritorio_id: str):
    usage = db.execute(
        text("""
            SELECT
                COALESCE(SUM(CASE WHEN ativo = 1 AND role = 'advogado' THEN 1 ELSE 0 END), 0) AS usuarios_ativos,
                COALESCE(SUM(CASE WHEN ativo = 1 AND role = 'advogado' THEN 1 ELSE 0 END), 0) AS advogados_ativos
            FROM usuarios
            WHERE escritorio_id = :eid
        """),
        {"eid": escritorio_id},
    ).mappings().first()
    return int(usage["usuarios_ativos"] or 0), int(usage["advogados_ativos"] or 0)


