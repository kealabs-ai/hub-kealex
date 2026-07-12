import os, uuid, enum
from datetime import datetime
from typing import Optional
import logging
from fastapi import FastAPI, HTTPException, Depends
from fastapi.middleware.cors import CORSMiddleware
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from pydantic import BaseModel
from jose import jwt, JWTError
from sqlalchemy import create_engine, Column, String, DateTime, Text, Integer
from sqlalchemy.orm import DeclarativeBase, Session, sessionmaker

logging.basicConfig(level=logging.DEBUG, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

def _get_database_url(default: str) -> str:
    raw = os.getenv("DATABASE_URL")
    if raw is None or raw.strip().lower() in ("", "null", "none"):
        return default
    return raw.strip()

DATABASE_URL = _get_database_url(
    "mysql+pymysql://u549746795_kealex:Sally2026%40%21%40@srv1078.hstgr.io:3306/u549746795_kealex"
)
SECRET_KEY = os.getenv("SECRET_KEY", "changeme-secret-key")
ALGORITHM = "HS256"

engine = create_engine(
    DATABASE_URL,
    pool_pre_ping=True,
    pool_recycle=280,
    pool_size=5,
    max_overflow=10,
)
SessionLocal = sessionmaker(bind=engine, autocommit=False, autoflush=False)
bearer = HTTPBearer()

class Base(DeclarativeBase): pass

class Cobranca(Base):
    __tablename__ = "cobrancas"
    id = Column(String(36), primary_key=True)
    tenant_id = Column(String(36), nullable=False)
    user_id = Column(String(36), nullable=False)
    processo_id = Column(String(36), nullable=False)
    cliente_id = Column(String(36), nullable=False)
    valor_centavos = Column(Integer, nullable=False)
    status = Column(String(50), default="pendente")
    fase_atual = Column(Integer, default=0)
    data_vencimento = Column(DateTime, nullable=True)
    data_pagamento = Column(DateTime, nullable=True)
    motivo_cancelamento = Column(String(500), nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

class HistoricoCobranca(Base):
    __tablename__ = "historico_cobrancas"
    id = Column(String(36), primary_key=True)
    cobranca_id = Column(String(36), nullable=False)
    acao = Column(String(100), nullable=False)
    fase_anterior = Column(Integer, nullable=True)
    fase_nova = Column(Integer, nullable=True)
    status_anterior = Column(String(50), nullable=True)
    status_novo = Column(String(50), nullable=True)
    observacao = Column(String(500), nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)

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
        raise HTTPException(401, "Token invalido")

app = FastAPI(title="svc-cobrancas")
app.add_middleware(CORSMiddleware, allow_origins=["*"], allow_methods=["*"], allow_headers=["*"])

@app.get("/health")
def health():
    return {"status": "healthy", "service": "svc-cobrancas"}

class CobrancaIn(BaseModel):
    processoId: str
    clienteId: str
    valorCentavos: int
    dataVencimento: Optional[str] = None

def _cobranca_to_dict(cobranca: Cobranca):
    fases_cobranca = ["Pendente", "Aguardando Pagamento", "Vencida", "Em Cobranca", "Pago"]
    return {
        "id": cobranca.id,
        "tenantId": cobranca.tenant_id,
        "processoId": cobranca.processo_id,
        "clienteId": cobranca.cliente_id,
        "valorCentavos": cobranca.valor_centavos,
        "status": cobranca.status,
        "faseAtual": cobranca.fase_atual,
        "faseLabel": fases_cobranca[cobranca.fase_atual] if cobranca.fase_atual < len(fases_cobranca) else "Desconhecida",
        "dataVencimento": cobranca.data_vencimento.isoformat() if cobranca.data_vencimento else None,
        "dataPagamento": cobranca.data_pagamento.isoformat() if cobranca.data_pagamento else None,
        "motivoCancelamento": cobranca.motivo_cancelamento,
        "createdAt": cobranca.created_at.isoformat(),
        "updatedAt": cobranca.updated_at.isoformat()
    }

def _get_proximas_acoes(cobranca: Cobranca):
    acoes = []
    if cobranca.status != "pago" and cobranca.status != "cancelado":
        acoes.append({"acao": "proxima_fase", "label": "Proxima Fase", "descricao": "Avancar para a proxima fase de cobranca"})
        acoes.append({"acao": "marcar_pago", "label": "Marcar como Pago", "descricao": "Registrar pagamento recebido"})
        acoes.append({"acao": "cancelar", "label": "Cancelar", "descricao": "Cancelar esta cobranca"})
    return acoes

@app.post("/k1/lex/cobrancas", status_code=201)
def criar_cobranca(body: CobrancaIn, db: Session = Depends(get_db), payload=Depends(verify_token)):
    try:
        logger.info(f"[CREATE_COBRANCA] Iniciando criacao de cobranca para processo: {body.processoId}")
        tenant_id = payload.get("tenant_id")
        
        cobranca = Cobranca(
            id=str(uuid.uuid4()),
            tenant_id=tenant_id,
            user_id=payload["sub"],
            processo_id=body.processoId,
            cliente_id=body.clienteId,
            valor_centavos=body.valorCentavos,
            data_vencimento=datetime.fromisoformat(body.dataVencimento) if body.dataVencimento else None,
            status="pendente",
            fase_atual=0
        )
        db.add(cobranca)
        db.commit()
        db.refresh(cobranca)
        logger.info(f"[CREATE_COBRANCA] Cobranca criada: {cobranca.id}")
        
        historico = HistoricoCobranca(
            id=str(uuid.uuid4()),
            cobranca_id=cobranca.id,
            acao="criada",
            status_novo="pendente",
            observacao="Cobranca criada"
        )
        db.add(historico)
        db.commit()
        logger.info(f"[CREATE_COBRANCA] Historico registrado")
        
        return _cobranca_to_dict(cobranca)
    except Exception as e:
        logger.error(f"[CREATE_COBRANCA] ERRO: {str(e)}", exc_info=True)
        db.rollback()
        raise HTTPException(500, f"Erro ao criar cobranca: {str(e)}")

@app.get("/k1/lex/cobrancas")
def listar_cobrancas(db: Session = Depends(get_db), payload=Depends(verify_token)):
    try:
        tenant_id = payload.get("tenant_id")
        cobrancas = db.query(Cobranca).filter_by(tenant_id=tenant_id).order_by(Cobranca.created_at.desc()).all()
        logger.info(f"[LIST_COBRANCAS] Total de cobrancas: {len(cobrancas)}")
        return [_cobranca_to_dict(c) for c in cobrancas]
    except Exception as e:
        logger.error(f"[LIST_COBRANCAS] ERRO: {str(e)}", exc_info=True)
        raise HTTPException(500, f"Erro ao listar cobrancas: {str(e)}")

@app.post("/k1/lex/cobrancas/get")
def get_cobranca(body: dict, db: Session = Depends(get_db), payload=Depends(verify_token)):
    try:
        cobranca_id = body.get("id")
        if not cobranca_id:
            raise HTTPException(400, "ID obrigatorio")
        
        tenant_id = payload.get("tenant_id")
        cobranca = db.query(Cobranca).filter_by(id=cobranca_id, tenant_id=tenant_id).first()
        if not cobranca:
            raise HTTPException(404, "Cobranca nao encontrada")
        
        logger.info(f"[GET_COBRANCA] Cobranca recuperada: {cobranca_id}")
        return _cobranca_to_dict(cobranca)
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"[GET_COBRANCA] ERRO: {str(e)}", exc_info=True)
        raise HTTPException(500, f"Erro ao obter cobranca: {str(e)}")

@app.post("/k1/lex/cobrancas/proxima-fase")
def proxima_fase_cobranca(body: dict, db: Session = Depends(get_db), payload=Depends(verify_token)):
    try:
        cobranca_id = body.get("id")
        if not cobranca_id:
            raise HTTPException(400, "ID obrigatorio")
        
        tenant_id = payload.get("tenant_id")
        cobranca = db.query(Cobranca).filter_by(id=cobranca_id, tenant_id=tenant_id).first()
        if not cobranca:
            raise HTTPException(404, "Cobranca nao encontrado")
        
        if cobranca.status == "pago" or cobranca.status == "cancelado":
            raise HTTPException(400, f"Nao e possivel avancar fase de cobranca com status {cobranca.status}")
        
        fases_cobranca = ["Pendente", "Aguardando Pagamento", "Vencida", "Em Cobranca", "Pago"]
        
        fase_anterior = cobranca.fase_atual
        nova_fase = min(cobranca.fase_atual + 1, len(fases_cobranca) - 1)
        
        cobranca.fase_atual = nova_fase
        cobranca.updated_at = datetime.utcnow()
        db.add(cobranca)
        
        historico = HistoricoCobranca(
            id=str(uuid.uuid4()),
            cobranca_id=cobranca.id,
            acao="fase_avancada",
            fase_anterior=fase_anterior,
            fase_nova=nova_fase,
            observacao=f"Avancado de {fases_cobranca[fase_anterior]} para {fases_cobranca[nova_fase]}"
        )
        db.add(historico)
        db.commit()
        
        logger.info(f"[PROXIMA_FASE] Fase avancada de {fase_anterior} para {nova_fase}")
        return _cobranca_to_dict(cobranca)
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"[PROXIMA_FASE] ERRO: {str(e)}", exc_info=True)
        db.rollback()
        raise HTTPException(500, f"Erro ao avancar fase: {str(e)}")

@app.post("/k1/lex/cobrancas/marcar-pago")
def marcar_pago(body: dict, db: Session = Depends(get_db), payload=Depends(verify_token)):
    try:
        cobranca_id = body.get("id")
        if not cobranca_id:
            raise HTTPException(400, "ID obrigatorio")
        
        tenant_id = payload.get("tenant_id")
        cobranca = db.query(Cobranca).filter_by(id=cobranca_id, tenant_id=tenant_id).first()
        if not cobranca:
            raise HTTPException(404, "Cobranca nao encontrado")
        
        if cobranca.status == "cancelado":
            raise HTTPException(400, "Nao e possivel marcar como pago uma cobranca cancelada")
        
        status_anterior = cobranca.status
        cobranca.status = "pago"
        cobranca.fase_atual = 4
        cobranca.data_pagamento = datetime.utcnow()
        cobranca.updated_at = datetime.utcnow()
        db.add(cobranca)
        
        historico = HistoricoCobranca(
            id=str(uuid.uuid4()),
            cobranca_id=cobranca.id,
            acao="marcado_pago",
            status_anterior=status_anterior,
            status_novo="pago",
            observacao=body.get("observacao", "Marcado como pago")
        )
        db.add(historico)
        db.commit()
        
        logger.info(f"[MARCAR_PAGO] Cobranca marcada como pago: {cobranca_id}")
        return _cobranca_to_dict(cobranca)
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"[MARCAR_PAGO] ERRO: {str(e)}", exc_info=True)
        db.rollback()
        raise HTTPException(500, f"Erro ao marcar como pago: {str(e)}")

@app.post("/k1/lex/cobrancas/cancelar")
def cancelar_cobranca(body: dict, db: Session = Depends(get_db), payload=Depends(verify_token)):
    try:
        cobranca_id = body.get("id")
        if not cobranca_id:
            raise HTTPException(400, "ID obrigatorio")
        
        tenant_id = payload.get("tenant_id")
        cobranca = db.query(Cobranca).filter_by(id=cobranca_id, tenant_id=tenant_id).first()
        if not cobranca:
            raise HTTPException(404, "Cobranca nao encontrado")
        
        if cobranca.status == "pago":
            raise HTTPException(400, "Nao e possivel cancelar uma cobranca ja paga")
        
        motivo = body.get("motivo", "Cancelado pelo usuario")
        status_anterior = cobranca.status
        
        cobranca.status = "cancelado"
        cobranca.motivo_cancelamento = motivo
        cobranca.updated_at = datetime.utcnow()
        db.add(cobranca)
        
        historico = HistoricoCobranca(
            id=str(uuid.uuid4()),
            cobranca_id=cobranca.id,
            acao="cancelada",
            status_anterior=status_anterior,
            status_novo="cancelado",
            observacao=motivo
        )
        db.add(historico)
        db.commit()
        
        logger.info(f"[CANCELAR] Cobranca cancelada: {cobranca_id}")
        return _cobranca_to_dict(cobranca)
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"[CANCELAR] ERRO: {str(e)}", exc_info=True)
        db.rollback()
        raise HTTPException(500, f"Erro ao cancelar cobranca: {str(e)}")

@app.post("/k1/lex/cobrancas/timeline")
def timeline_cobranca(body: dict, db: Session = Depends(get_db), payload=Depends(verify_token)):
    try:
        cobranca_id = body.get("id")
        if not cobranca_id:
            raise HTTPException(400, "ID obrigatorio")
        
        tenant_id = payload.get("tenant_id")
        cobranca = db.query(Cobranca).filter_by(id=cobranca_id, tenant_id=tenant_id).first()
        if not cobranca:
            raise HTTPException(404, "Cobranca nao encontrado")
        
        fases_cobranca = [
            {"ordem": 0, "label": "Pendente", "descricao": "Cobranca criada e aguardando processamento"},
            {"ordem": 1, "label": "Aguardando Pagamento", "descricao": "Aguardando confirmacao de pagamento"},
            {"ordem": 2, "label": "Vencida", "descricao": "Prazo de pagamento vencido"},
            {"ordem": 3, "label": "Em Cobranca", "descricao": "Em processo de cobranca ativa"},
            {"ordem": 4, "label": "Pago", "descricao": "Cobranca paga com sucesso"}
        ]
        
        historico = db.query(HistoricoCobranca).filter_by(cobranca_id=cobranca_id).order_by(HistoricoCobranca.created_at).all()
        
        timeline = []
        for h in historico:
            timeline.append({
                "id": h.id,
                "acao": h.acao,
                "fase_anterior": h.fase_anterior,
                "fase_nova": h.fase_nova,
                "status_anterior": h.status_anterior,
                "status_novo": h.status_novo,
                "observacao": h.observacao,
                "data": h.created_at.isoformat()
            })
        
        logger.info(f"[TIMELINE] Timeline recuperada: {len(timeline)} eventos")
        return {
            "cobranca_id": cobranca_id,
            "status_atual": cobranca.status,
            "fase_atual": cobranca.fase_atual,
            "valor_centavos": cobranca.valor_centavos,
            "data_vencimento": cobranca.data_vencimento.isoformat() if cobranca.data_vencimento else None,
            "data_pagamento": cobranca.data_pagamento.isoformat() if cobranca.data_pagamento else None,
            "fases": fases_cobranca,
            "timeline": timeline,
            "proximas_acoes": _get_proximas_acoes(cobranca)
        }
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"[TIMELINE] ERRO: {str(e)}", exc_info=True)
        raise HTTPException(500, f"Erro ao obter timeline: {str(e)}")
