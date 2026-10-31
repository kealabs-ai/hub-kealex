from datetime import datetime
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from app.api.dependencies import base_guard
from app.api.schemas.user_schema import ChavePublicaIn
from app.application.use_cases.user_presenter import public_key_to_dict
from app.infrastructure.database.models.user_model import Usuario, UsuarioChavePublica
from app.infrastructure.database.session import get_db

router = APIRouter()

@router.get("/v1/lex/usuarios/chaves-publicas")
@router.get("/v1/lex/usuarios/me/chaves-publicas")
def list_my_public_keys(db: Session = Depends(get_db), payload=Depends(base_guard)):
    user_id = payload.get("sub")
    tenant_id = payload.get("tenant_id") or user_id
    user = db.query(Usuario.id).filter_by(id=user_id, tenant_id=tenant_id).first()
    if not user:
        raise HTTPException(404, "UsuÃ¡rio nÃ£o encontrado")
    items = db.query(UsuarioChavePublica).filter_by(user_id=user_id).order_by(UsuarioChavePublica.orgao).all()
    return [public_key_to_dict(item) for item in items]


@router.post("/v1/lex/usuarios/chaves-publicas")
@router.post("/v1/lex/usuarios/me/chaves-publicas")
def save_my_public_key(body: ChavePublicaIn, db: Session = Depends(get_db), payload=Depends(base_guard)):
    user_id = payload.get("sub")
    tenant_id = payload.get("tenant_id") or user_id
    user = db.query(Usuario.id).filter_by(id=user_id, tenant_id=tenant_id).first()
    if not user:
        raise HTTPException(404, "UsuÃ¡rio nÃ£o encontrado")
    orgao = body.orgao.strip()
    chave_publica = body.chavePublica.strip()
    if not orgao or len(orgao) > 120:
        raise HTTPException(422, "Informe um Ã³rgÃ£o vÃ¡lido (atÃ© 120 caracteres).")
    if not chave_publica or len(chave_publica) > 10000:
        raise HTTPException(422, "Informe uma chave pÃºblica vÃ¡lida (atÃ© 10.000 caracteres).")
    item = db.query(UsuarioChavePublica).filter_by(user_id=user_id, orgao=orgao).with_for_update().first()
    if item:
        item.chave_publica = chave_publica
        item.updated_at = datetime.utcnow()
    else:
        item = UsuarioChavePublica(user_id=user_id, orgao=orgao, chave_publica=chave_publica)
        db.add(item)
    db.commit()
    db.refresh(item)
    return public_key_to_dict(item)


@router.post("/v1/lex/usuarios/chaves-publicas/{key_id}")
@router.post("/v1/lex/usuarios/me/chaves-publicas/{key_id}")
def update_my_public_key(key_id: str, body: ChavePublicaIn, db: Session = Depends(get_db), payload=Depends(base_guard)):
    user_id = payload.get("sub")
    tenant_id = payload.get("tenant_id") or user_id
    if not db.query(Usuario.id).filter_by(id=user_id, tenant_id=tenant_id).first():
        raise HTTPException(404, "UsuÃ¡rio nÃ£o encontrado")

    item = db.query(UsuarioChavePublica).filter_by(id=key_id, user_id=user_id).first()
    if not item:
        raise HTTPException(404, "Chave pÃºblica nÃ£o encontrada")
    orgao = body.orgao.strip()
    chave_publica = body.chavePublica.strip()
    if not orgao or len(orgao) > 120:
        raise HTTPException(422, "Informe um Ã³rgÃ£o vÃ¡lido (atÃ© 120 caracteres).")
    if not chave_publica or len(chave_publica) > 10000:
        raise HTTPException(422, "Informe uma chave pÃºblica vÃ¡lida (atÃ© 10.000 caracteres).")
    duplicate = db.query(UsuarioChavePublica.id).filter(
        UsuarioChavePublica.user_id == user_id,
        UsuarioChavePublica.orgao == orgao,
        UsuarioChavePublica.id != key_id,
    ).first()
    if duplicate:
        raise HTTPException(409, "JÃ¡ existe uma chave cadastrada para este Ã³rgÃ£o.")
    item.orgao = orgao
    item.chave_publica = chave_publica
    item.updated_at = datetime.utcnow()
    db.commit()
    db.refresh(item)
    return public_key_to_dict(item)


@router.delete("/v1/lex/usuarios/chaves-publicas/{key_id}")
@router.delete("/v1/lex/usuarios/me/chaves-publicas/{key_id}")
def delete_my_public_key(key_id: str, db: Session = Depends(get_db), payload=Depends(base_guard)):
    user_id = payload.get("sub")
    tenant_id = payload.get("tenant_id") or user_id
    if not db.query(Usuario.id).filter_by(id=user_id, tenant_id=tenant_id).first():
        raise HTTPException(404, "UsuÃ¡rio nÃ£o encontrado")
    item = db.query(UsuarioChavePublica).filter_by(id=key_id, user_id=user_id).first()
    if not item:
        raise HTTPException(404, "Chave pÃºblica nÃ£o encontrada")
    db.delete(item)
    db.commit()
    return {"ok": True}
