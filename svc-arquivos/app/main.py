import os
from pathlib import Path
from uuid import UUID
from uuid import uuid4

from fastapi import Depends, FastAPI, File, HTTPException, UploadFile
from fastapi.responses import FileResponse
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from jose import JWTError, jwt

app = FastAPI(title="svc-arquivos")
bearer = HTTPBearer()
SECRET = os.getenv("KEALEX_SECRET_KEY") or os.getenv("KEALEX_JWT_SECRET")
UPLOAD_DIR = Path(os.getenv("UPLOAD_DIR", "/data/uploads")).resolve()
MAX_UPLOAD_BYTES = int(os.getenv("MAX_UPLOAD_BYTES", "104857600"))


def current_owner(credentials: HTTPAuthorizationCredentials = Depends(bearer)):
    if not SECRET:
        raise HTTPException(503, "Autenticação não configurada")
    try:
        claims = jwt.decode(credentials.credentials, SECRET, algorithms=["HS256"])
    except JWTError as exc:
        raise HTTPException(401, "Token inválido") from exc
    tenant_id, user_id = claims.get("tenant_id"), claims.get("sub")
    if not tenant_id or not user_id:
        raise HTTPException(401, "Token sem tenant ou usuário")
    return str(tenant_id), str(user_id)


def owner_dir(owner):
    tenant_id, user_id = owner
    try:
        tenant_id, user_id = str(UUID(tenant_id)), str(UUID(user_id))
    except ValueError as exc:
        raise HTTPException(401, "Identidade inválida") from exc
    path = (UPLOAD_DIR / tenant_id / user_id).resolve()
    if not path.is_relative_to(UPLOAD_DIR):
        raise HTTPException(400, "Caminho inválido")
    path.mkdir(parents=True, exist_ok=True)
    return path


@app.get("/health")
def health():
    return {"status": "ok", "service": "svc-arquivos"}


@app.post("/v1/lex/arquivos", status_code=201)
async def upload(file: UploadFile = File(...), owner=Depends(current_owner)):
    directory = owner_dir(owner)
    file_id = str(uuid4())
    destination = directory / file_id
    size = 0
    try:
        with destination.open("wb") as stream:
            while chunk := await file.read(1024 * 1024):
                size += len(chunk)
                if size > MAX_UPLOAD_BYTES:
                    raise HTTPException(413, "Arquivo excede o limite permitido")
                stream.write(chunk)
    except Exception:
        destination.unlink(missing_ok=True)
        raise
    finally:
        await file.close()
    return {"id": file_id, "name": Path(file.filename or "arquivo").name, "size": size}


@app.get("/v1/lex/arquivos/{file_id}")
def download(file_id: str, owner=Depends(current_owner)):
    try:
        file_id = str(UUID(file_id))
    except ValueError as exc:
        raise HTTPException(404, "Arquivo não encontrado") from exc
    path = owner_dir(owner) / file_id
    if not path.is_file():
        raise HTTPException(404, "Arquivo não encontrado")
    return FileResponse(path)


@app.delete("/v1/lex/arquivos/{file_id}", status_code=204)
def delete(file_id: str, owner=Depends(current_owner)):
    try:
        file_id = str(UUID(file_id))
    except ValueError as exc:
        raise HTTPException(404, "Arquivo não encontrado") from exc
    path = owner_dir(owner) / file_id
    if not path.is_file():
        raise HTTPException(404, "Arquivo não encontrado")
    path.unlink()
