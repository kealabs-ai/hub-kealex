import json
import os
from pathlib import Path

import httpx
import aiofiles
from sqlalchemy.orm import Session

from app.core.config import STORAGE_PATH
from app.domain.entities.repository_types import StatusEnum, TipoRepositorioEnum
from app.infrastructure.database.models.repository_model import Arquivo, Repositorio


async def scan_repository(repository: Repositorio, db: Session):
    if repository.tipo == TipoRepositorioEnum.local:
        await _scan_local(repository, db)
    elif repository.tipo == TipoRepositorioEnum.cdn:
        await _scan_cdn(repository, db)
    elif repository.tipo == TipoRepositorioEnum.gdrive:
        await _scan_gdrive(repository, db)


async def _scan_local(repository: Repositorio, db: Session):
    path = Path(repository.caminho_local)
    if not path.exists():
        repository.status = StatusEnum.erro
        return

    for file_path in path.rglob("*"):
        if file_path.is_file():
            db.add(Arquivo(
                tenant_id=repository.tenant_id,
                repositorio_id=repository.id,
                nome=file_path.name,
                caminho=str(file_path.relative_to(path)),
                tamanho_bytes=file_path.stat().st_size,
                metadados=json.dumps({}),
            ))


async def _scan_cdn(repository: Repositorio, db: Session):
    try:
        async with httpx.AsyncClient() as client:
            response = await client.get(repository.url, timeout=10)
            if response.status_code == 200:
                files = response.json() if response.headers.get("content-type") == "application/json" else []
                for item in files:
                    db.add(Arquivo(
                        tenant_id=repository.tenant_id,
                        repositorio_id=repository.id,
                        nome=item.get("name", ""),
                        caminho=item.get("path", ""),
                        tamanho_bytes=item.get("size", 0),
                        metadados=json.dumps(item),
                    ))
    except Exception:
        repository.status = StatusEnum.erro


async def _scan_gdrive(repository: Repositorio, db: Session):
    try:
        token = os.getenv("GDRIVE_TOKEN")
        if not token:
            repository.status = StatusEnum.erro
            return

        query = f"'{repository.gdrive_folder_id}' in parents and trashed=false"
        url = f"https://www.googleapis.com/drive/v3/files?q={query}&fields=id,name,size,mimeType"
        async with httpx.AsyncClient() as client:
            response = await client.get(
                url,
                headers={"Authorization": f"Bearer {token}"},
                timeout=10,
            )
            if response.status_code == 200:
                for item in response.json().get("files", []):
                    db.add(Arquivo(
                        tenant_id=repository.tenant_id,
                        repositorio_id=repository.id,
                        nome=item.get("name", ""),
                        caminho=item.get("id", ""),
                        tamanho_bytes=item.get("size", 0),
                        tipo_mime=item.get("mimeType"),
                        metadados=json.dumps(item),
                    ))
    except Exception:
        repository.status = StatusEnum.erro


async def save_uploaded_file(repository_id: str, file, tenant_id: str, db: Session):
    file_path = Path(STORAGE_PATH) / repository_id / file.filename
    file_path.parent.mkdir(parents=True, exist_ok=True)
    content = await file.read()
    async with aiofiles.open(file_path, "wb") as output:
        await output.write(content)
    uploaded = Arquivo(
        tenant_id=tenant_id,
        repositorio_id=repository_id,
        nome=file.filename,
        caminho=str(file_path.relative_to(STORAGE_PATH)),
        tamanho_bytes=len(content),
        tipo_mime=file.content_type,
        metadados=json.dumps({}),
    )
    db.add(uploaded)
    db.commit()
    db.refresh(uploaded)
    return uploaded
