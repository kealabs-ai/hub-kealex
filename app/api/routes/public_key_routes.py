from fastapi import APIRouter

from app.legacy_context import (
    ChavePublicaIn,
    Depends,
    HTTPException,
    Session,
    UserApiKey,
    UserApiKeyCreate,
    UserApiKeyUpdate,
    UsuarioChavePublica,
    _current_api_key_owner,
    _decrypt_user_api_key,
    _encrypt_user_api_key,
    _public_key_to_dict,
    _user_api_key_json,
    _validate_model_provider,
    _validate_user_api_key,
    _validated_public_key,
    datetime,
    get_db,
    verify_token,
)

router = APIRouter()


@router.get("/v1/lex/usuarios/chaves-publicas")
@router.get("/v1/lex/usuarios/me/chaves-publicas")
def list_my_public_keys(db: Session = Depends(get_db), payload=Depends(verify_token)):
    user_id, _ = _current_api_key_owner(db, payload)
    rows = db.query(UsuarioChavePublica).filter_by(user_id=user_id).order_by(UsuarioChavePublica.orgao).all()
    return [_public_key_to_dict(row) for row in rows]


@router.post("/v1/lex/usuarios/chaves-publicas")
@router.post("/v1/lex/usuarios/me/chaves-publicas")
def save_my_public_key(body: ChavePublicaIn, db: Session = Depends(get_db), payload=Depends(verify_token)):
    user_id, _ = _current_api_key_owner(db, payload)
    orgao, chave_publica = _validated_public_key(body)
    row = db.query(UsuarioChavePublica).filter_by(user_id=user_id, orgao=orgao).with_for_update().first()
    if row:
        row.chave_publica = chave_publica
        row.updated_at = datetime.utcnow()
    else:
        row = UsuarioChavePublica(user_id=user_id, orgao=orgao, chave_publica=chave_publica)
        db.add(row)
    db.commit()
    db.refresh(row)
    return _public_key_to_dict(row)


@router.post("/v1/lex/usuarios/chaves-publicas/{key_id}")
@router.post("/v1/lex/usuarios/me/chaves-publicas/{key_id}")
def update_my_public_key(key_id: str, body: ChavePublicaIn, db: Session = Depends(get_db), payload=Depends(verify_token)):
    user_id, _ = _current_api_key_owner(db, payload)
    row = db.query(UsuarioChavePublica).filter_by(id=key_id, user_id=user_id).first()
    if not row:
        raise HTTPException(404, "Chave pública não encontrada")
    orgao, chave_publica = _validated_public_key(body)
    duplicate = db.query(UsuarioChavePublica.id).filter(
        UsuarioChavePublica.user_id == user_id,
        UsuarioChavePublica.orgao == orgao,
        UsuarioChavePublica.id != key_id,
    ).first()
    if duplicate:
        raise HTTPException(409, "Já existe uma chave cadastrada para este órgão.")
    row.orgao = orgao
    row.chave_publica = chave_publica
    row.updated_at = datetime.utcnow()
    db.commit()
    db.refresh(row)
    return _public_key_to_dict(row)


@router.delete("/v1/lex/usuarios/chaves-publicas/{key_id}")
@router.delete("/v1/lex/usuarios/me/chaves-publicas/{key_id}")
def delete_my_public_key(key_id: str, db: Session = Depends(get_db), payload=Depends(verify_token)):
    user_id, _ = _current_api_key_owner(db, payload)
    row = db.query(UsuarioChavePublica).filter_by(id=key_id, user_id=user_id).first()
    if not row:
        raise HTTPException(404, "Chave pública não encontrada")
    db.delete(row)
    db.commit()
    return {"ok": True}


@router.get("/k1/lex/configuracoes/ia/minhas-chaves")
def list_my_ia_keys(db: Session = Depends(get_db), payload=Depends(verify_token)):
    user_id, tenant_id = _current_api_key_owner(db, payload)
    rows = db.query(UserApiKey).filter_by(user_id=user_id, tenant_id=tenant_id).order_by(UserApiKey.created_at.desc()).all()
    return [_user_api_key_json(row) for row in rows]


@router.post("/k1/lex/configuracoes/ia/minhas-chaves", status_code=201)
def create_my_ia_key(body: UserApiKeyCreate, db: Session = Depends(get_db), payload=Depends(verify_token)):
    user_id, tenant_id = _current_api_key_owner(db, payload)
    _validate_model_provider(body.provider, body.model)
    _validate_user_api_key(body.provider, body.api_key.strip())
    if db.query(UserApiKey).filter_by(user_id=user_id, provider=body.provider, model=body.model).first():
        raise HTTPException(409, "Já existe uma chave cadastrada para este provedor e modelo.")
    if body.is_active:
        db.query(UserApiKey).filter_by(user_id=user_id, tenant_id=tenant_id, is_active=True).update({"is_active": False}, synchronize_session=False)
    row = UserApiKey(tenant_id=tenant_id, user_id=user_id, created_by=user_id, provider=body.provider, model=body.model, api_key_encrypted=_encrypt_user_api_key(body.api_key.strip()), is_active=body.is_active)
    db.add(row)
    db.commit()
    db.refresh(row)
    return _user_api_key_json(row)


@router.put("/k1/lex/configuracoes/ia/minhas-chaves/{key_id}")
def update_my_ia_key(key_id: str, body: UserApiKeyUpdate, db: Session = Depends(get_db), payload=Depends(verify_token)):
    user_id, tenant_id = _current_api_key_owner(db, payload)
    row = db.query(UserApiKey).filter_by(id=key_id, user_id=user_id, tenant_id=tenant_id).first()
    if not row:
        raise HTTPException(404, "Chave de IA não encontrada.")
    provider = body.provider or row.provider
    model = body.model or row.model
    _validate_model_provider(provider, model)
    duplicate = db.query(UserApiKey).filter(UserApiKey.user_id == user_id, UserApiKey.provider == provider, UserApiKey.model == model, UserApiKey.id != row.id).first()
    if duplicate:
        raise HTTPException(409, "Já existe uma chave cadastrada para este provedor e modelo.")
    secret = body.api_key.strip() if body.api_key and body.api_key.strip() else _decrypt_user_api_key(row.api_key_encrypted)
    _validate_user_api_key(provider, secret)
    if body.is_active is True:
        db.query(UserApiKey).filter(UserApiKey.user_id == user_id, UserApiKey.tenant_id == tenant_id, UserApiKey.id != row.id, UserApiKey.is_active.is_(True)).update({"is_active": False}, synchronize_session=False)
    row.provider, row.model, row.api_key_encrypted = provider, model, _encrypt_user_api_key(secret)
    if body.is_active is not None:
        row.is_active = body.is_active
    row.updated_at = datetime.utcnow()
    db.commit()
    db.refresh(row)
    return _user_api_key_json(row)


@router.delete("/k1/lex/configuracoes/ia/minhas-chaves/{key_id}", status_code=204)
def delete_my_ia_key(key_id: str, db: Session = Depends(get_db), payload=Depends(verify_token)):
    user_id, tenant_id = _current_api_key_owner(db, payload)
    row = db.query(UserApiKey).filter_by(id=key_id, user_id=user_id, tenant_id=tenant_id).first()
    if not row:
        raise HTTPException(404, "Chave de IA não encontrada.")
    db.delete(row)
    db.commit()
