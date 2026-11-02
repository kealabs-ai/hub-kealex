import json
from datetime import datetime

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.api.dependencies import verify_token
from app.api.schemas.repository_schema import (
    RepositorioDeleteIn,
    RepositorioGetIn,
    RepositorioIn,
    RepositorioUpdate,
)
from app.application.use_cases.repository_presenter import repository_to_dict
from app.domain.entities.repository_types import TipoRepositorioEnum
from app.infrastructure.database.models.repository_model import Arquivo, Repositorio
from app.infrastructure.database.session import get_db

router = APIRouter()


@router.get("/k1/lex/repositorios")
def list_repositorios(db: Session = Depends(get_db), payload=Depends(verify_token)):
    tenant_id = payload.get("tenant_id")
    return [repository_to_dict(item) for item in db.query(Repositorio).filter_by(tenant_id=tenant_id).all()]


@router.post("/k1/lex/repositorios/get")
def get_repositorio(body: RepositorioGetIn, db: Session = Depends(get_db), payload=Depends(verify_token)):
    repository = db.query(Repositorio).filter_by(id=body.id, tenant_id=payload.get("tenant_id")).first()
    if not repository:
        raise HTTPException(404, "Repositório não encontrado")
    return repository_to_dict(repository)


@router.post("/k1/lex/repositorios", status_code=201)
def create_repositorio(body: RepositorioIn, db: Session = Depends(get_db), payload=Depends(verify_token)):
    required_fields = {
        TipoRepositorioEnum.local: (body.caminhoLocal, "caminhoLocal obrigatório para repositório local"),
        TipoRepositorioEnum.cdn: (body.url, "url obrigatória para repositório CDN"),
        TipoRepositorioEnum.gdrive: (body.gdriveFolder, "gdriveFolder obrigatório para Google Drive"),
    }
    value, message = required_fields[body.tipo]
    if not value:
        raise HTTPException(400, message)

    repository = Repositorio(
        tenant_id=payload.get("tenant_id"),
        user_id=payload["sub"],
        nome=body.nome,
        tipo=body.tipo,
        url=body.url,
        caminho_local=body.caminhoLocal,
        gdrive_folder_id=body.gdriveFolder,
        descricao=body.descricao,
        metadados=json.dumps({}),
    )
    db.add(repository)
    db.commit()
    db.refresh(repository)
    return repository_to_dict(repository)


@router.post("/k1/lex/repositorios/update")
def update_repositorio(body: RepositorioUpdate, db: Session = Depends(get_db), payload=Depends(verify_token)):
    repository = db.query(Repositorio).filter_by(id=body.id, tenant_id=payload.get("tenant_id")).first()
    if not repository:
        raise HTTPException(404, "Repositório não encontrado")

    for key, value in body.model_dump(exclude_none=True, exclude={"id"}).items():
        setattr(repository, key, value)
    repository.updated_at = datetime.utcnow()
    db.commit()
    db.refresh(repository)
    return repository_to_dict(repository)


@router.post("/k1/lex/repositorios/delete")
def delete_repositorio(body: RepositorioDeleteIn, db: Session = Depends(get_db), payload=Depends(verify_token)):
    repository = db.query(Repositorio).filter_by(id=body.id, tenant_id=payload.get("tenant_id")).first()
    if not repository:
        raise HTTPException(404, "Repositório não encontrado")

    db.query(Arquivo).filter_by(repositorio_id=repository.id).delete()
    db.delete(repository)
    db.commit()
    return {"ok": True}
