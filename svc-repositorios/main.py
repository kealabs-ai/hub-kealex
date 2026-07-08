import os, uuid, enum, json
from datetime import datetime
from typing import Optional
from pathlib import Path
import aiofiles
import httpx
from fastapi import FastAPI, HTTPException, Depends, UploadFile, File
from fastapi.middleware.cors import CORSMiddleware
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from pydantic import BaseModel
from jose import jwt, JWTError
from sqlalchemy import create_engine, Column, String, DateTime, Text, Integer, Enum as SAEnum
from sqlalchemy.orm import DeclarativeBase, Session, sessionmaker

def _get_database_url(default: str) -> str:
    raw = os.getenv("DATABASE_URL")
    if raw is None or raw.strip().lower() in ("", "null", "none"):
        return default
    return raw.strip()

DATABASE_URL = _get_database_url(
    "mysql+pymysql://u549746795_kealex:Sally2026%40%21%40@srv1078.hstgr.io:3306/u549746795_kealex"
)
SECRET_KEY   = os.getenv("SECRET_KEY", "changeme-secret-key")
ALGORITHM    = "HS256"
STORAGE_PATH = os.getenv("STORAGE_PATH", "/tmp/repositorios")

engine       = create_engine(
    DATABASE_URL,
    pool_pre_ping=True,
    pool_recycle=280,
    pool_size=5,
    max_overflow=10,
)
SessionLocal = sessionmaker(bind=engine, autocommit=False, autoflush=False)
bearer       = HTTPBearer()

os.makedirs(STORAGE_PATH, exist_ok=True)

class Base(DeclarativeBase): pass

class TipoRepositorioEnum(str, enum.Enum):
    local    = "local"
    cdn      = "cdn"
    gdrive   = "gdrive"

class StatusEnum(str, enum.Enum):
    ativo    = "ativo"
    inativo  = "inativo"
    erro     = "erro"

class Repositorio(Base):
    __tablename__ = "repositorios"
    id            = Column(String(36),   primary_key=True, default=lambda: str(uuid.uuid4()))
    tenant_id     = Column(String(36),   nullable=False)
    user_id       = Column(String(36),   nullable=False)
    nome          = Column(String(255),  nullable=False)
    tipo          = Column(SAEnum(TipoRepositorioEnum, name="tipo_repo_enum"), nullable=False)
    status        = Column(SAEnum(StatusEnum, name="status_repo_enum"), default=StatusEnum.ativo)
    url           = Column(String(1000), nullable=True)
    caminho_local = Column(String(1000), nullable=True)
    gdrive_folder_id = Column(String(255), nullable=True)
    descricao     = Column(Text, nullable=True)
    metadados     = Column(Text, nullable=True)
    created_at    = Column(DateTime, default=datetime.utcnow)
    updated_at    = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

class Arquivo(Base):
    __tablename__ = "arquivos"
    id            = Column(String(36),   primary_key=True, default=lambda: str(uuid.uuid4()))
    tenant_id     = Column(String(36),   nullable=False)
    repositorio_id = Column(String(36),  nullable=False)
    nome          = Column(String(255),  nullable=False)
    caminho       = Column(String(1000), nullable=False)
    tipo_mime     = Column(String(100),  nullable=True)
    tamanho_bytes = Column(Integer,      default=0)
    hash_arquivo  = Column(String(64),   nullable=True)
    metadados     = Column(Text,         nullable=True)
    created_at    = Column(DateTime,     default=datetime.utcnow)
    updated_at    = Column(DateTime,     default=datetime.utcnow, onupdate=datetime.utcnow)

Base.metadata.create_all(engine)

def get_db():
    db = SessionLocal()
    try:
        yield db
    except Exception:
        db.rollback()
        raise
    finally:
        db.close()

def verify_token(creds: HTTPAuthorizationCredentials = Depends(bearer)):
    try:
        return jwt.decode(creds.credentials, SECRET_KEY, algorithms=[ALGORITHM])
    except JWTError:
        raise HTTPException(401, "Token inválido")

app = FastAPI(title="svc-repositorios")
app.add_middleware(CORSMiddleware, allow_origins=["*"], allow_methods=["*"], allow_headers=["*"])

@app.get("/health")
def health():
    return {"status": "ok", "service": "svc-repositorios"}

class RepositorioIn(BaseModel):
    nome:           str
    tipo:           TipoRepositorioEnum
    url:            Optional[str] = None
    caminhoLocal:   Optional[str] = None
    gdriveFolder:   Optional[str] = None
    descricao:      Optional[str] = None

class RepositorioUpdate(BaseModel):
    id:             str
    nome:           Optional[str] = None
    status:         Optional[StatusEnum] = None
    descricao:      Optional[str] = None

class RepositorioGetIn(BaseModel):
    id: str

class RepositorioDeleteIn(BaseModel):
    id: str

def _repo_to_dict(r: Repositorio):
    meta = json.loads(r.metadados) if r.metadados else {}
    return {
        "id": r.id, "tenantId": r.tenant_id, "userId": r.user_id, "nome": r.nome,
        "tipo": r.tipo, "status": r.status, "url": r.url, "caminhoLocal": r.caminho_local,
        "gdriveFolder": r.gdrive_folder_id, "descricao": r.descricao, "metadados": meta,
        "createdAt": r.created_at.isoformat(), "updatedAt": r.updated_at.isoformat()
    }

def _arquivo_to_dict(a: Arquivo):
    meta = json.loads(a.metadados) if a.metadados else {}
    return {
        "id": a.id, "tenantId": a.tenant_id, "repositorioId": a.repositorio_id,
        "nome": a.nome, "caminho": a.caminho, "tipoMime": a.tipo_mime,
        "tamanhoBytes": a.tamanho_bytes, "hashArquivo": a.hash_arquivo, "metadados": meta,
        "createdAt": a.created_at.isoformat(), "updatedAt": a.updated_at.isoformat()
    }

@app.get("/k1/lex/repositorios")
def list_repositorios(db: Session = Depends(get_db), payload=Depends(verify_token)):
    tenant_id = payload.get("tenant_id")
    return [_repo_to_dict(r) for r in db.query(Repositorio).filter_by(tenant_id=tenant_id).all()]

@app.post("/k1/lex/repositorios/get")
def get_repositorio(body: RepositorioGetIn, db: Session = Depends(get_db), payload=Depends(verify_token)):
    tenant_id = payload.get("tenant_id")
    r = db.query(Repositorio).filter_by(id=body.id, tenant_id=tenant_id).first()
    if not r:
        raise HTTPException(404, "Repositório não encontrado")
    return _repo_to_dict(r)

@app.post("/k1/lex/repositorios", status_code=201)
def create_repositorio(body: RepositorioIn, db: Session = Depends(get_db), payload=Depends(verify_token)):
    tenant_id = payload.get("tenant_id")
    
    if body.tipo == TipoRepositorioEnum.local and not body.caminhoLocal:
        raise HTTPException(400, "caminhoLocal obrigatório para repositório local")
    if body.tipo == TipoRepositorioEnum.cdn and not body.url:
        raise HTTPException(400, "url obrigatória para repositório CDN")
    if body.tipo == TipoRepositorioEnum.gdrive and not body.gdriveFolder:
        raise HTTPException(400, "gdriveFolder obrigatório para Google Drive")
    
    r = Repositorio(
        tenant_id=tenant_id, user_id=payload["sub"], nome=body.nome, tipo=body.tipo,
        url=body.url, caminho_local=body.caminhoLocal, gdrive_folder_id=body.gdriveFolder,
        descricao=body.descricao, metadados=json.dumps({})
    )
    db.add(r); db.commit(); db.refresh(r)
    return _repo_to_dict(r)

@app.post("/k1/lex/repositorios/update")
def update_repositorio(body: RepositorioUpdate, db: Session = Depends(get_db), payload=Depends(verify_token)):
    tenant_id = payload.get("tenant_id")
    r = db.query(Repositorio).filter_by(id=body.id, tenant_id=tenant_id).first()
    if not r:
        raise HTTPException(404, "Repositório não encontrado")
    
    for k, v in body.model_dump(exclude_none=True, exclude={"id"}).items():
        setattr(r, k, v)
    r.updated_at = datetime.utcnow()
    db.commit(); db.refresh(r)
    return _repo_to_dict(r)

@app.post("/k1/lex/repositorios/delete")
def delete_repositorio(body: RepositorioDeleteIn, db: Session = Depends(get_db), payload=Depends(verify_token)):
    tenant_id = payload.get("tenant_id")
    r = db.query(Repositorio).filter_by(id=body.id, tenant_id=tenant_id).first()
    if not r:
        raise HTTPException(404, "Repositório não encontrado")
    
    db.query(Arquivo).filter_by(repositorio_id=r.id).delete()
    db.delete(r); db.commit()
    return {"ok": True}

@app.get("/k1/lex/repositorios/{repo_id}/arquivos")
def list_arquivos(repo_id: str, db: Session = Depends(get_db), payload=Depends(verify_token)):
    tenant_id = payload.get("tenant_id")
    r = db.query(Repositorio).filter_by(id=repo_id, tenant_id=tenant_id).first()
    if not r:
        raise HTTPException(404, "Repositório não encontrado")
    
    return [_arquivo_to_dict(a) for a in db.query(Arquivo).filter_by(repositorio_id=repo_id).all()]

@app.post("/k1/lex/repositorios/{repo_id}/scan")
async def scan_repositorio(repo_id: str, db: Session = Depends(get_db), payload=Depends(verify_token)):
    tenant_id = payload.get("tenant_id")
    r = db.query(Repositorio).filter_by(id=repo_id, tenant_id=tenant_id).first()
    if not r:
        raise HTTPException(404, "Repositório não encontrado")
    
    db.query(Arquivo).filter_by(repositorio_id=repo_id).delete()
    
    if r.tipo == TipoRepositorioEnum.local:
        await _scan_local(r, db)
    elif r.tipo == TipoRepositorioEnum.cdn:
        await _scan_cdn(r, db)
    elif r.tipo == TipoRepositorioEnum.gdrive:
        await _scan_gdrive(r, db)
    
    db.commit()
    return {"ok": True, "mensagem": "Repositório escaneado com sucesso"}

async def _scan_local(r: Repositorio, db: Session):
    path = Path(r.caminho_local)
    if not path.exists():
        r.status = StatusEnum.erro
        return
    
    for file_path in path.rglob("*"):
        if file_path.is_file():
            a = Arquivo(
                tenant_id=r.tenant_id, repositorio_id=r.id, nome=file_path.name,
                caminho=str(file_path.relative_to(path)), tamanho_bytes=file_path.stat().st_size,
                metadados=json.dumps({})
            )
            db.add(a)

async def _scan_cdn(r: Repositorio, db: Session):
    try:
        async with httpx.AsyncClient() as client:
            resp = await client.get(r.url, timeout=10)
            if resp.status_code == 200:
                files = resp.json() if resp.headers.get("content-type") == "application/json" else []
                for f in files:
                    a = Arquivo(
                        tenant_id=r.tenant_id, repositorio_id=r.id, nome=f.get("name", ""),
                        caminho=f.get("path", ""), tamanho_bytes=f.get("size", 0),
                        metadados=json.dumps(f)
                    )
                    db.add(a)
    except Exception as e:
        r.status = StatusEnum.erro

async def _scan_gdrive(r: Repositorio, db: Session):
    try:
        gdrive_token = os.getenv("GDRIVE_TOKEN")
        if not gdrive_token:
            r.status = StatusEnum.erro
            return
        
        async with httpx.AsyncClient() as client:
            headers = {"Authorization": f"Bearer {gdrive_token}"}
            query = f"'{r.gdrive_folder_id}' in parents and trashed=false"
            url = f"https://www.googleapis.com/drive/v3/files?q={query}&fields=id,name,size,mimeType"
            resp = await client.get(url, headers=headers, timeout=10)
            
            if resp.status_code == 200:
                data = resp.json()
                for f in data.get("files", []):
                    a = Arquivo(
                        tenant_id=r.tenant_id, repositorio_id=r.id, nome=f.get("name", ""),
                        caminho=f.get("id", ""), tamanho_bytes=f.get("size", 0),
                        tipo_mime=f.get("mimeType"), metadados=json.dumps(f)
                    )
                    db.add(a)
    except Exception as e:
        r.status = StatusEnum.erro

@app.post("/k1/lex/repositorios/{repo_id}/upload")
async def upload_arquivo(repo_id: str, file: UploadFile = File(...), 
                        db: Session = Depends(get_db), payload=Depends(verify_token)):
    tenant_id = payload.get("tenant_id")
    r = db.query(Repositorio).filter_by(id=repo_id, tenant_id=tenant_id).first()
    if not r:
        raise HTTPException(404, "Repositório não encontrado")
    
    if r.tipo != TipoRepositorioEnum.local:
        raise HTTPException(400, "Upload apenas para repositórios locais")
    
    file_path = Path(STORAGE_PATH) / repo_id / file.filename
    file_path.parent.mkdir(parents=True, exist_ok=True)
    
    content = await file.read()
    async with aiofiles.open(file_path, "wb") as f:
        await f.write(content)
    
    a = Arquivo(
        tenant_id=tenant_id, repositorio_id=repo_id, nome=file.filename,
        caminho=str(file_path.relative_to(STORAGE_PATH)), tamanho_bytes=len(content),
        tipo_mime=file.content_type, metadados=json.dumps({})
    )
    db.add(a); db.commit(); db.refresh(a)
    return _arquivo_to_dict(a)
