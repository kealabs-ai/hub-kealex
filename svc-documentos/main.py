import os, uuid, enum
from datetime import datetime
from typing import Optional
from fastapi import FastAPI, HTTPException, Depends
from fastapi.middleware.cors import CORSMiddleware
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from pydantic import BaseModel
from jose import jwt, JWTError
from sqlalchemy import create_engine, Column, String, Integer, DateTime, Enum as SAEnum
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

engine       = create_engine(
    DATABASE_URL,
    pool_pre_ping=True,
    pool_recycle=280,
    pool_size=5,
    max_overflow=10,
)
SessionLocal = sessionmaker(bind=engine, autocommit=False, autoflush=False)
bearer       = HTTPBearer()

class Base(DeclarativeBase): pass

class TipoEnum(str, enum.Enum):
    peticao     = "peticao"
    contrato    = "contrato"
    comprovante = "comprovante"
    outro       = "outro"

class StatusEnum(str, enum.Enum):
    pendente  = "pendente"
    aprovado  = "aprovado"
    rejeitado = "rejeitado"

class Documento(Base):
    __tablename__ = "documentos"
    id               = Column(String(36),   primary_key=True, default=lambda: str(uuid.uuid4()))
    tenant_id        = Column(String(36),   nullable=False)
    user_id          = Column(String(36),   nullable=False)
    escritorio_id    = Column(String(36),   nullable=True)
    processo_id      = Column(String(36),   nullable=False)
    uploadado_por_id = Column(String(36),   nullable=False)
    nome             = Column(String(255),  nullable=False)
    tipo             = Column(SAEnum(TipoEnum,   name="tipo_doc_enum"),   nullable=False)
    status           = Column(SAEnum(StatusEnum, name="status_doc_enum"), default=StatusEnum.pendente)
    url_arquivo      = Column(String(1000), nullable=False)
    tamanho_bytes    = Column(Integer,      default=0)
    created_at       = Column(DateTime,     default=datetime.utcnow)
    updated_at       = Column(DateTime,     default=datetime.utcnow, onupdate=datetime.utcnow)

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

app = FastAPI(title="svc-documentos")
app.add_middleware(CORSMiddleware, allow_origins=["*"], allow_methods=["*"], allow_headers=["*"])

@app.get("/health")
def health():
    return {"status": "ok", "service": "svc-documentos"}

class DocumentoIn(BaseModel):
    processoId:    str
    nome:          str
    tipo:          TipoEnum
    urlArquivo:    str
    tamanhoBytes:  int = 0
    escritorioId:  Optional[str] = None

class DocumentoGetIn(BaseModel):
    id: str

class DocumentoByProcessoIn(BaseModel):
    processoId: str

class DocumentoUpdate(BaseModel):
    id:         str
    nome:       Optional[str]        = None
    tipo:       Optional[TipoEnum]   = None
    status:     Optional[StatusEnum] = None
    urlArquivo: Optional[str]        = None

class DocumentoDeleteIn(BaseModel):
    id: str

def _to_dict(d: Documento):
    return {
        "id": d.id, "tenantId": d.tenant_id, "userId": d.user_id, "escritorioId": d.escritorio_id,
        "processoId": d.processo_id, "uploadadoPorId": d.uploadado_por_id, "nome": d.nome, "tipo": d.tipo,
        "status": d.status, "urlArquivo": d.url_arquivo, "tamanhoBytes": d.tamanho_bytes,
        "createdAt": d.created_at.isoformat(), "updatedAt": d.updated_at.isoformat()
    }

@app.get("/v1/lex/documentos")
def list_docs(db: Session = Depends(get_db), payload=Depends(verify_token)):
    tenant_id = payload.get("tenant_id") or payload.get("sub")
    return [_to_dict(d) for d in db.query(Documento).filter_by(tenant_id=tenant_id).all()]

@app.post("/v1/lex/documentos/get")
def get_doc(body: DocumentoGetIn, db: Session = Depends(get_db), payload=Depends(verify_token)):
    tenant_id = payload.get("tenant_id") or payload.get("sub")
    d = db.query(Documento).filter_by(id=body.id, tenant_id=tenant_id).first()
    if not d:
        raise HTTPException(404, "Não encontrado")
    return _to_dict(d)

@app.post("/v1/lex/documentos/by-processo")
def by_processo(body: DocumentoByProcessoIn, db: Session = Depends(get_db), payload=Depends(verify_token)):
    tenant_id = payload.get("tenant_id") or payload.get("sub")
    return [_to_dict(d) for d in db.query(Documento).filter_by(
        tenant_id=tenant_id, processo_id=body.processoId).all()]

@app.post("/v1/lex/documentos", status_code=201)
def create_doc(body: DocumentoIn, db: Session = Depends(get_db), payload=Depends(verify_token)):
    tenant_id = payload.get("tenant_id") or payload.get("sub")
    d = Documento(tenant_id=tenant_id, user_id=payload["sub"], escritorio_id=body.escritorioId,
                  processo_id=body.processoId, uploadado_por_id=payload["sub"], nome=body.nome, tipo=body.tipo,
                  url_arquivo=body.urlArquivo, tamanho_bytes=body.tamanhoBytes)
    db.add(d); db.commit(); db.refresh(d)
    return _to_dict(d)

@app.post("/v1/lex/documentos/update")
def update_doc(body: DocumentoUpdate, db: Session = Depends(get_db), payload=Depends(verify_token)):
    tenant_id = payload.get("tenant_id") or payload.get("sub")
    d = db.query(Documento).filter_by(id=body.id, tenant_id=tenant_id).first()
    if not d:
        raise HTTPException(404, "Não encontrado")
    data = body.model_dump(exclude_none=True, exclude={"id"})
    if "urlArquivo" in data:
        d.url_arquivo = data.pop("urlArquivo")
    for k, v in data.items():
        setattr(d, k, v)
    d.updated_at = datetime.utcnow()
    db.commit(); db.refresh(d)
    return _to_dict(d)

@app.post("/v1/lex/documentos/delete")
def delete_doc(body: DocumentoDeleteIn, db: Session = Depends(get_db), payload=Depends(verify_token)):
    tenant_id = payload.get("tenant_id") or payload.get("sub")
    d = db.query(Documento).filter_by(id=body.id, tenant_id=tenant_id).first()
    if not d:
        raise HTTPException(404, "Não encontrado")
    db.delete(d); db.commit()
    return {"ok": True}
