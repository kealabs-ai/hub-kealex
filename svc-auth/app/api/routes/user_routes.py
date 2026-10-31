from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from app.infrastructure.database.models.auth_models import Usuario, Escritorio
from app.infrastructure.database.session import get_db
from app.api.dependencies import require_active_trial

router = APIRouter()

@router.get("/k1/lex/auth/me")
def me(payload=Depends(require_active_trial), db: Session = Depends(get_db)):
    user = db.query(Usuario).filter_by(id=payload.get("sub"), tenant_id=payload.get("tenant_id")).first()
    if not user:
        raise HTTPException(404, "Usuário não encontrado")
    office = db.query(Escritorio).filter_by(id=user.escritorio_id, tenant_id=user.tenant_id).first() if user.escritorio_id else None
    return {
        **payload,
        "escritorioId": user.escritorio_id,
        "codigoEscritorio": user.codigo,
        "escritorioNome": office.nome if office else None,
        "modalidade": "escritorio" if user.escritorio_id else "autonomo",
    }


