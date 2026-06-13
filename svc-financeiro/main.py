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

class StatusEnum(str, enum.Enum):
    pendente  = "pendente"
    pago      = "pago"
    vencido   = "vencido"
    cancelado = "cancelado"

class Honorario(Base):
    __tablename__ = "honorarios"
    id              = Column(String(36),  primary_key=True, default=lambda: str(uuid.uuid4()))
    tenant_id       = Column(String(36),  nullable=False)
    user_id         = Column(String(36),  nullable=False)
    escritorio_id   = Column(String(36),  nullable=True)
    processo_id     = Column(String(36),  nullable=False)
    cliente_id      = Column(String(36),  nullable=False)
    advogado_id     = Column(String(36),  nullable=False)
    descricao       = Column(String(500), default="")
    valor_centavos  = Column(Integer,     nullable=False)
    data_vencimento = Column(String(10),  nullable=False)
    data_pagamento  = Column(String(10),  nullable=True)
    status          = Column(SAEnum(StatusEnum, name="status_honorario_enum"), default=StatusEnum.pendente)
    created_at      = Column(DateTime,    default=datetime.utcnow)
    updated_at      = Column(DateTime,    default=datetime.utcnow, onupdate=datetime.utcnow)

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

app = FastAPI(title="svc-financeiro")
app.add_middleware(CORSMiddleware, allow_origins=["*"], allow_methods=["*"], allow_headers=["*"])

@app.get("/health")
def health():
    return {"status": "ok", "service": "svc-financeiro"}

class HonorarioIn(BaseModel):
    processoId:     str
    clienteId:      str
    descricao:      str = ""
    valorCentavos:  int
    dataVencimento: str
    escritorioId:   Optional[str] = None

class HonorarioGetIn(BaseModel):
    id: str

class HonorarioUpdate(BaseModel):
    id:             str
    descricao:      Optional[str]        = None
    valorCentavos:  Optional[int]        = None
    dataVencimento: Optional[str]        = None
    dataPagamento:  Optional[str]        = None
    status:         Optional[StatusEnum] = None

class HonorarioDeleteIn(BaseModel):
    id: str

def _to_dict(h: Honorario):
    return {
        "id": h.id, "tenantId": h.tenant_id, "userId": h.user_id, "escritorioId": h.escritorio_id,
        "processoId": h.processo_id, "clienteId": h.cliente_id, "advogadoId": h.advogado_id, "descricao": h.descricao,
        "valorCentavos": h.valor_centavos, "dataVencimento": h.data_vencimento,
        "dataPagamento": h.data_pagamento, "status": h.status,
        "createdAt": h.created_at.isoformat(), "updatedAt": h.updated_at.isoformat()
    }

@app.get("/v1/lex/financeiro")
def list_honorarios(db: Session = Depends(get_db), payload=Depends(verify_token)):
    tenant_id = payload.get("tenant_id") or payload.get("sub")
    return [_to_dict(h) for h in db.query(Honorario).filter_by(tenant_id=tenant_id).all()]

@app.get("/v1/lex/financeiro/dashboard")
def dashboard(db: Session = Depends(get_db), payload=Depends(verify_token)):
    tenant_id = payload.get("tenant_id") or payload.get("sub")
    rows = db.query(Honorario).filter_by(tenant_id=tenant_id).all()
    return {
        "totalPendente": sum(h.valor_centavos for h in rows if h.status == StatusEnum.pendente),
        "totalPago":     sum(h.valor_centavos for h in rows if h.status == StatusEnum.pago),
        "totalVencido":  sum(h.valor_centavos for h in rows if h.status == StatusEnum.vencido),
        "totalGeral":    sum(h.valor_centavos for h in rows),
    }

@app.post("/v1/lex/financeiro/get")
def get_honorario(body: HonorarioGetIn, db: Session = Depends(get_db), payload=Depends(verify_token)):
    tenant_id = payload.get("tenant_id") or payload.get("sub")
    h = db.query(Honorario).filter_by(id=body.id, tenant_id=tenant_id).first()
    if not h:
        raise HTTPException(404, "Não encontrado")
    return _to_dict(h)

@app.post("/v1/lex/financeiro", status_code=201)
def create_honorario(body: HonorarioIn, db: Session = Depends(get_db), payload=Depends(verify_token)):
    tenant_id = payload.get("tenant_id") or payload.get("sub")
    h = Honorario(tenant_id=tenant_id, user_id=payload["sub"], escritorio_id=body.escritorioId,
                  processo_id=body.processoId, cliente_id=body.clienteId, advogado_id=payload["sub"],
                  descricao=body.descricao, valor_centavos=body.valorCentavos,
                  data_vencimento=body.dataVencimento)
    db.add(h); db.commit(); db.refresh(h)
    return _to_dict(h)

@app.post("/v1/lex/financeiro/update")
def update_honorario(body: HonorarioUpdate, db: Session = Depends(get_db), payload=Depends(verify_token)):
    tenant_id = payload.get("tenant_id") or payload.get("sub")
    h = db.query(Honorario).filter_by(id=body.id, tenant_id=tenant_id).first()
    if not h:
        raise HTTPException(404, "Não encontrado")
    data = body.model_dump(exclude_none=True, exclude={"id"})
    mapping = {"valorCentavos": "valor_centavos", "dataVencimento": "data_vencimento", "dataPagamento": "data_pagamento"}
    for k, v in data.items():
        setattr(h, mapping.get(k, k), v)
    h.updated_at = datetime.utcnow()
    db.commit(); db.refresh(h)
    return _to_dict(h)

@app.post("/v1/lex/financeiro/delete")
def delete_honorario(body: HonorarioDeleteIn, db: Session = Depends(get_db), payload=Depends(verify_token)):
    tenant_id = payload.get("tenant_id") or payload.get("sub")
    h = db.query(Honorario).filter_by(id=body.id, tenant_id=tenant_id).first()
    if not h:
        raise HTTPException(404, "Não encontrado")
    db.delete(h); db.commit()
    return {"ok": True}
