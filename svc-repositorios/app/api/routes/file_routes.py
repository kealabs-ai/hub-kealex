from fastapi import APIRouter, Depends, File, HTTPException, UploadFile
from sqlalchemy.orm import Session

from app.api.dependencies import verify_token
from app.application.use_cases.repository_presenter import file_to_dict
from app.application.use_cases.repository_scanner import save_uploaded_file, scan_repository
from app.domain.entities.repository_types import TipoRepositorioEnum
from app.infrastructure.database.models.repository_model import Arquivo, Repositorio
from app.infrastructure.database.session import get_db

router = APIRouter()


@router.get("/k1/lex/repositorios/{repo_id}/arquivos")
def list_arquivos(repo_id: str, db: Session = Depends(get_db), payload=Depends(verify_token)):
    repository = db.query(Repositorio).filter_by(id=repo_id, tenant_id=payload.get("tenant_id")).first()
    if not repository:
        raise HTTPException(404, "Repositório não encontrado")
    files = db.query(Arquivo).filter_by(repositorio_id=repo_id).all()
    return [file_to_dict(item) for item in files]


@router.post("/k1/lex/repositorios/{repo_id}/scan")
async def scan_repositorio(repo_id: str, db: Session = Depends(get_db), payload=Depends(verify_token)):
    repository = db.query(Repositorio).filter_by(id=repo_id, tenant_id=payload.get("tenant_id")).first()
    if not repository:
        raise HTTPException(404, "Repositório não encontrado")

    db.query(Arquivo).filter_by(repositorio_id=repo_id).delete()
    await scan_repository(repository, db)
    db.commit()
    return {"ok": True, "mensagem": "Repositório escaneado com sucesso"}


@router.post("/k1/lex/repositorios/{repo_id}/upload")
async def upload_arquivo(
    repo_id: str,
    file: UploadFile = File(...),
    db: Session = Depends(get_db),
    payload=Depends(verify_token),
):
    tenant_id = payload.get("tenant_id")
    repository = db.query(Repositorio).filter_by(id=repo_id, tenant_id=tenant_id).first()
    if not repository:
        raise HTTPException(404, "Repositório não encontrado")
    if repository.tipo != TipoRepositorioEnum.local:
        raise HTTPException(400, "Upload apenas para repositórios locais")

    uploaded = await save_uploaded_file(repo_id, file, tenant_id, db)
    return file_to_dict(uploaded)
