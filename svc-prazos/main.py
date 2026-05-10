import os, uuid, enum
from datetime import datetime, date, timedelta
from typing import Optional
from fastapi import FastAPI, HTTPException, Depends
from fastapi.middleware.cors import CORSMiddleware
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from pydantic import BaseModel
from jose import jwt, JWTError
from sqlalchemy import create_engine, Column, String, DateTime, Enum as SAEnum
from sqlalchemy.orm import DeclarativeBase, Session, sessionmaker

DATABASE_URL = os.getenv("DATABASE_URL", "mysql+pymysql://u549746795_kealex:Sally2026%40%21%40@srv1078.hstgr.io:3306/u549746795_kealex")
SECRET_KEY   = os.getenv("SECRET_KEY", "changeme-secret-key")
ALGORITHM    = "HS256"

engine       = create_engine(DATABASE_URL, pool_pre_ping=True, pool_recycle=280, pool_size=5, max_overflow=10)
SessionLocal = sessionmaker(bind=engine, autocommit=False, autoflush=False)
bearer       = HTTPBearer()

class Base(DeclarativeBase): pass

class StatusEnum(str, enum.Enum):
    pendente  = "pendente"
    concluido = "concluido"
    vencido   = "vencido"

class Prazo(Base):
    __tablename__ = "prazos"
    id              = Column(String(36),   primary_key=True, default=lambda: str(uuid.uuid4()))
    tenant_id       = Column(String(36),   nullable=False)
    user_id         = Column(String(36),   nullable=False)
    escritorio_id   = Column(String(36),   nullable=True)
    processo_id     = Column(String(36),   nullable=False)
    advogado_id     = Column(String(36),   nullable=False)
    titulo          = Column(String(255),  nullable=False)
    descricao       = Column(String(1000), default="")
    data_vencimento = Column(String(10),   nullable=False)
    status          = Column(SAEnum(StatusEnum, name="status_prazo_enum"), default=StatusEnum.pendente)
    created_at      = Column(DateTime,     default=datetime.utcnow)
    updated_at      = Column(DateTime,     default=datetime.utcnow, onupdate=datetime.utcnow)

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

app = FastAPI(title="svc-prazos")
app.add_middleware(CORSMiddleware, allow_origins=["*"], allow_methods=["*"], allow_headers=["*"])

class PrazoIn(BaseModel):
    processoId:     str
    titulo:         str
    descricao:      str = ""
    dataVencimento: str
    escritorioId:   Optional[str] = None

class PrazoGetIn(BaseModel):
    id: str

class PrazoByProcessoIn(BaseModel):
    processoId: str

class PrazoVencendoIn(BaseModel):
    dias: int = 7

class PrazoUpdate(BaseModel):
    id:             str
    titulo:         Optional[str]        = None
    descricao:      Optional[str]        = None
    dataVencimento: Optional[str]        = None
    status:         Optional[StatusEnum] = None

class PrazoDeleteIn(BaseModel):
    id: str

def _to_dict(p: Prazo):
    return {
        "id": p.id, "tenantId": p.tenant_id, "userId": p.user_id, "escritorioId": p.escritorio_id,
        "processoId": p.processo_id, "advogadoId": p.advogado_id, "titulo": p.titulo, "descricao": p.descricao,
        "dataVencimento": p.data_vencimento, "status": p.status,
        "createdAt": p.created_at.isoformat(), "updatedAt": p.updated_at.isoformat()
    }

@app.get("/prazos")
def list_prazos(db: Session = Depends(get_db), payload=Depends(verify_token)):
    tenant_id = payload.get("tenant_id") or payload.get("sub")
    return [_to_dict(p) for p in db.query(Prazo).filter_by(tenant_id=tenant_id).all()]

@app.post("/prazos/get")
def get_prazo(body: PrazoGetIn, db: Session = Depends(get_db), payload=Depends(verify_token)):
    tenant_id = payload.get("tenant_id") or payload.get("sub")
    p = db.query(Prazo).filter_by(id=body.id, tenant_id=tenant_id).first()
    if not p:
        raise HTTPException(404, "Não encontrado")
    return _to_dict(p)

@app.post("/prazos/vencendo")
def vencendo(body: PrazoVencendoIn, db: Session = Depends(get_db), payload=Depends(verify_token)):
    tenant_id = payload.get("tenant_id") or payload.get("sub")
    hoje   = date.today().isoformat()
    limite = (date.today() + timedelta(days=body.dias)).isoformat()
    rows = db.query(Prazo).filter(
        Prazo.tenant_id == tenant_id,
        Prazo.data_vencimento >= hoje,
        Prazo.data_vencimento <= limite,
        Prazo.status == StatusEnum.pendente
    ).all()
    return [_to_dict(p) for p in rows]

@app.post("/prazos/by-processo")
def by_processo(body: PrazoByProcessoIn, db: Session = Depends(get_db), payload=Depends(verify_token)):
    tenant_id = payload.get("tenant_id") or payload.get("sub")
    return [_to_dict(p) for p in db.query(Prazo).filter_by(
        tenant_id=tenant_id, processo_id=body.processoId).all()]

@app.post("/prazos", status_code=201)
def create_prazo(body: PrazoIn, db: Session = Depends(get_db), payload=Depends(verify_token)):
    tenant_id = payload.get("tenant_id") or payload.get("sub")
    p = Prazo(tenant_id=tenant_id, user_id=payload["sub"], escritorio_id=body.escritorioId,
              processo_id=body.processoId, advogado_id=payload["sub"], titulo=body.titulo,
              descricao=body.descricao, data_vencimento=body.dataVencimento)
    db.add(p); db.commit(); db.refresh(p)
    return _to_dict(p)

@app.post("/prazos/update")
def update_prazo(body: PrazoUpdate, db: Session = Depends(get_db), payload=Depends(verify_token)):
    tenant_id = payload.get("tenant_id") or payload.get("sub")
    p = db.query(Prazo).filter_by(id=body.id, tenant_id=tenant_id).first()
    if not p:
        raise HTTPException(404, "Não encontrado")
    data = body.model_dump(exclude_none=True, exclude={"id"})
    if "dataVencimento" in data:
        p.data_vencimento = data.pop("dataVencimento")
    for k, v in data.items():
        setattr(p, k, v)
    p.updated_at = datetime.utcnow()
    db.commit(); db.refresh(p)
    return _to_dict(p)

@app.post("/prazos/delete")
def delete_prazo(body: PrazoDeleteIn, db: Session = Depends(get_db), payload=Depends(verify_token)):
    tenant_id = payload.get("tenant_id") or payload.get("sub")
    p = db.query(Prazo).filter_by(id=body.id, tenant_id=tenant_id).first()
    if not p:
        raise HTTPException(404, "Não encontrado")
    db.delete(p); db.commit()
    return {"ok": True}
