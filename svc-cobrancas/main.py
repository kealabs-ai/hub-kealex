import os, uuid, enum, sys, re, hmac
from datetime import datetime, timezone
from typing import Optional
import logging
import httpx
from fastapi import FastAPI, HTTPException, Depends, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from pydantic import BaseModel
from jose import jwt, JWTError
from sqlalchemy import create_engine, Column, String, DateTime, Text, Integer
from sqlalchemy.engine import URL, make_url
from sqlalchemy.orm import DeclarativeBase, Session, sessionmaker
from dotenv import load_dotenv

load_dotenv()
sys.path.insert(0, "/app")
try:
    from trial_guard import require_active_trial
except ImportError:
    require_active_trial = None

logging.basicConfig(level=logging.DEBUG, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

def _get_database_url():
    host = os.getenv("KEALEX_DB_HOST")
    database = os.getenv("KEALEX_DB_NAME")
    username = os.getenv("KEALEX_DB_USER")
    password = os.getenv("KEALEX_DB_PASSWORD")
    if host and database and username and password is not None:
        return URL.create(
            drivername="mysql+pymysql",
            username=username,
            password=password,
            host=host,
            port=int(os.getenv("KEALEX_DB_PORT", "3306")),
            database=database,
        )
    raw = os.getenv("KEALEX_DATABASE_URL")
    if raw is None or raw.strip().lower() in ("", "null", "none"):
        raise RuntimeError("Configure KEALEX_DB_HOST, KEALEX_DB_NAME, KEALEX_DB_USER e KEALEX_DB_PASSWORD (ou KEALEX_DATABASE_URL)")
    return make_url(raw.strip())

KEALEX_DATABASE_URL = _get_database_url()
KEALEX_SECRET_KEY = os.getenv("KEALEX_SECRET_KEY") or os.getenv("KEALEX_JWT_SECRET")
if not KEALEX_SECRET_KEY:
    raise RuntimeError("KEALEX_SECRET_KEY ou KEALEX_JWT_SECRET precisa estar configurada no ambiente")
ALGORITHM = "HS256"

engine = create_engine(
    KEALEX_DATABASE_URL,
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

class AsaasWebhookEvent(Base):
    __tablename__ = "asaas_webhook_events"
    id = Column(String(100), primary_key=True)  # event id vindo do Asaas
    event = Column(String(100), nullable=False)
    payload = Column(Text, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)

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
        return jwt.decode(creds.credentials, KEALEX_SECRET_KEY, algorithms=[ALGORITHM])
    except JWTError:
        raise HTTPException(401, "Token invalido")

_guard = require_active_trial if require_active_trial else verify_token

KEALEX_ASAAS_API_KEY = os.getenv("KEALEX_ASAAS_API_KEY", "")
ASAAS_BASE = os.getenv("KEALEX_ASAAS_BASE_URL", "https://api-sandbox.asaas.com/v3").rstrip("/")
KEALEX_ASAAS_WEBHOOK_TOKEN = os.getenv("KEALEX_ASAAS_WEBHOOK_TOKEN", "")

def _now():
    return datetime.now(timezone.utc).replace(tzinfo=None)

def _build_asaas_payload(body, cobranca):
    p = {
        "billingType": body.billingType,
        "customer": body.customer.strip(),
        "value": round(cobranca.valor_centavos / 100, 2),
        "dueDate": cobranca.data_vencimento.date().isoformat() if cobranca.data_vencimento else _now().date().isoformat(),
        "description": body.description or f"Cobranca {cobranca.id}",
        "externalReference": cobranca.id,
    }
    if body.billingType == "CREDIT_CARD":
        if body.creditCardToken:
            p["creditCardToken"] = body.creditCardToken
        else:
            p["creditCard"] = body.creditCard.model_dump()
            p["creditCardHolderInfo"] = body.creditCardHolderInfo.model_dump(exclude_none=True)
    return p

app = FastAPI(title="svc-cobrancas")
app.add_middleware(CORSMiddleware, allow_origins=["*"], allow_methods=["*"], allow_headers=["*"])

@app.on_event("startup")
def startup_event():
    try:
        Base.metadata.create_all(engine)
    except Exception as e:
        print(f"[ERRO] Database init falhou: {type(e).__name__}: {str(e)}")
        import traceback
        traceback.print_exc()

@app.get("/health")
def health():
    return {"status": "healthy", "service": "svc-cobrancas"}

# Alias: suporte a /k1/lex/cobrancas (legado) e /cobrancas (via stripprefix /v1/lex)
PREFIX = "/cobrancas"

class CobrancaIn(BaseModel):
    processoId: str
    clienteId: str
    valorCentavos: int
    dataVencimento: Optional[str] = None

class CreditCardIn(BaseModel):
    holderName: str
    number: str
    expiryMonth: str
    expiryYear: str
    ccv: str

class CreditCardHolderInfoIn(BaseModel):
    name: str
    email: str
    cpfCnpj: str
    postalCode: str
    addressNumber: str
    addressComplement: Optional[str] = None
    phone: str

class PagamentoIn(BaseModel):
    cobrancaId: str
    customer: str
    billingType: str
    description: Optional[str] = None
    creditCardToken: Optional[str] = None
    creditCard: Optional[CreditCardIn] = None
    creditCardHolderInfo: Optional[CreditCardHolderInfoIn] = None

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

@app.post("/v1/lex/cobrancas", status_code=201)
@app.post("/k1/lex/cobrancas", status_code=201)
@app.post(PREFIX, status_code=201, include_in_schema=False)
def criar_cobranca(body: CobrancaIn, db: Session = Depends(get_db), payload=Depends(_guard)):
    try:
        safe_id = re.sub(r'[^a-zA-Z0-9\-]', '', body.processoId)
        logger.info(f"[CREATE_COBRANCA] Iniciando criacao de cobranca para processo: {safe_id}")
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

@app.post("/v1/lex/cobrancas/pagamento")
@app.post("/k1/lex/cobrancas/pagamento")
@app.post(f"{PREFIX}/pagamento", include_in_schema=False)
def criar_pagamento(body: PagamentoIn, db: Session = Depends(get_db), payload=Depends(_guard)):
    if body.billingType not in ("PIX", "CREDIT_CARD"):
        raise HTTPException(400, "billingType invalido. Use 'PIX' ou 'CREDIT_CARD'")
    if not body.customer.strip():
        raise HTTPException(400, "customer (ID do cliente no ASAAS) e obrigatorio")
    if body.billingType == "CREDIT_CARD" and not body.creditCardToken and not body.creditCard:
        raise HTTPException(400, "Informe creditCardToken ou creditCard para pagamento com cartao")
    if body.billingType == "CREDIT_CARD" and body.creditCard and not body.creditCardHolderInfo:
        raise HTTPException(400, "creditCardHolderInfo e obrigatorio quando creditCard e informado")
    if not KEALEX_ASAAS_API_KEY:
        raise HTTPException(500, "KEALEX_ASAAS_API_KEY nao configurada")

    cobranca = db.query(Cobranca).filter_by(
        id=body.cobrancaId, tenant_id=payload.get("tenant_id")
    ).first()
    if not cobranca:
        raise HTTPException(404, "Cobranca nao encontrada")
    if cobranca.status in ("pago", "cancelado"):
        raise HTTPException(400, f"Cobranca com status '{cobranca.status}' nao pode ser paga")

    payload_asaas = _build_asaas_payload(body, cobranca)
    try:
        response = httpx.post(
            f"{ASAAS_BASE}/payments",
            json=payload_asaas,
            headers={
                "accept": "application/json",
                "content-type": "application/json",
                "access_token": KEALEX_ASAAS_API_KEY,
                "User-Agent": "Kealex/1.0.0",
            },
            timeout=15,
        )
    except httpx.RequestError as exc:
        logger.error("Falha de conexao com ASAAS: %s", exc)
        raise HTTPException(502, "Erro ao conectar com gateway de pagamento")

    if response.status_code not in (200, 201):
        logger.error("ASAAS recusou pagamento: status=%s body=%s", response.status_code, response.text)
        raise HTTPException(502, "ASAAS nao conseguiu criar o pagamento")

    asaas_data = response.json()
    status_anterior = cobranca.status
    cobranca.status = "aguardando_pagamento"
    cobranca.fase_atual = max(cobranca.fase_atual, 1)
    cobranca.updated_at = _now()
    db.add(HistoricoCobranca(
        id=str(uuid.uuid4()), cobranca_id=cobranca.id, acao="pagamento_iniciado",
        status_anterior=status_anterior, status_novo=cobranca.status,
        observacao=f"billingType={body.billingType}, asaas_id={asaas_data.get('id')}",
    ))
    db.commit()
    return {
        "cobrancaId": cobranca.id,
        "asaasId": asaas_data.get("id"),
        "billingType": asaas_data.get("billingType"),
        "status": asaas_data.get("status"),
        "value": asaas_data.get("value"),
        "dueDate": asaas_data.get("dueDate"),
        "invoiceUrl": asaas_data.get("invoiceUrl"),
        "pixQrCodeUrl": asaas_data.get("pixQrCodeUrl"),
    }

@app.get("/v1/lex/cobrancas")
@app.get("/k1/lex/cobrancas")
@app.get(PREFIX, include_in_schema=False)
def listar_cobrancas(db: Session = Depends(get_db), payload=Depends(_guard)):
    try:
        tenant_id = payload.get("tenant_id")
        cobrancas = db.query(Cobranca).filter_by(tenant_id=tenant_id).order_by(Cobranca.created_at.desc()).all()
        logger.info(f"[LIST_COBRANCAS] Total de cobrancas: {len(cobrancas)}")
        return [_cobranca_to_dict(c) for c in cobrancas]
    except Exception as e:
        logger.error(f"[LIST_COBRANCAS] ERRO: {str(e)}", exc_info=True)
        raise HTTPException(500, f"Erro ao listar cobrancas: {str(e)}")

@app.post("/v1/lex/cobrancas/get")
@app.post("/k1/lex/cobrancas/get")
@app.post(f"{PREFIX}/get", include_in_schema=False)
def get_cobranca(body: dict, db: Session = Depends(get_db), payload=Depends(_guard)):
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

@app.post("/v1/lex/cobrancas/proxima-fase")
@app.post("/k1/lex/cobrancas/proxima-fase")
@app.post(f"{PREFIX}/proxima-fase", include_in_schema=False)
def proxima_fase_cobranca(body: dict, db: Session = Depends(get_db), payload=Depends(_guard)):
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
        cobranca.updated_at = _now()
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

@app.post("/v1/lex/cobrancas/marcar-pago")
@app.post("/k1/lex/cobrancas/marcar-pago")
@app.post(f"{PREFIX}/marcar-pago", include_in_schema=False)
def marcar_pago(body: dict, db: Session = Depends(get_db), payload=Depends(_guard)):
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
        cobranca.data_pagamento = _now()
        cobranca.updated_at = _now()
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

@app.post("/v1/lex/cobrancas/cancelar")
@app.post("/k1/lex/cobrancas/cancelar")
@app.post(f"{PREFIX}/cancelar", include_in_schema=False)
def cancelar_cobranca(body: dict, db: Session = Depends(get_db), payload=Depends(_guard)):
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
        cobranca.updated_at = _now()
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

@app.post("/v1/lex/cobrancas/timeline")
@app.post("/k1/lex/cobrancas/timeline")
@app.post(f"{PREFIX}/timeline", include_in_schema=False)
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
        
        timeline = [
            {"id": h.id, "acao": h.acao, "fase_anterior": h.fase_anterior, "fase_nova": h.fase_nova,
             "status_anterior": h.status_anterior, "status_novo": h.status_novo,
             "observacao": h.observacao, "data": h.created_at.isoformat()}
            for h in historico
        ]
        
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

# ── Webhook ───────────────────────────────────────────────────────────────────

# Mapeamento evento Asaas → (status_interno, fase, acao_historico)
_EVENTO_MAP = {
    "PAYMENT_CONFIRMED":    ("pago",                4, "webhook_pago"),
    "PAYMENT_RECEIVED":     ("pago",                4, "webhook_pago"),
    "PAYMENT_OVERDUE":      ("vencida",             2, "webhook_vencida"),
    "PAYMENT_DELETED":      ("cancelado",           None, "webhook_cancelado"),
    "PAYMENT_REFUNDED":     ("cancelado",           None, "webhook_estornado"),
    "PAYMENT_CHARGEBACK_REQUESTED": ("cancelado",   None, "webhook_chargeback"),
}

def _verify_webhook_token(token: str | None) -> bool:
    if not KEALEX_ASAAS_WEBHOOK_TOKEN or not token:
        return False
    return hmac.compare_digest(
        token.encode("utf-8"),
        KEALEX_ASAAS_WEBHOOK_TOKEN.encode("utf-8"),
    )

@app.post("/v1/lex/cobrancas/webhook")
@app.post("/k1/lex/cobrancas/webhook")
@app.post(f"{PREFIX}/webhook", include_in_schema=False)
async def webhook_asaas(request: Request, db: Session = Depends(get_db)):
    import json as _json

    token = request.headers.get("asaas-access-token")
    if not _verify_webhook_token(token):
        logging.warning("[WEBHOOK] Token invalido ou ausente")
        raise HTTPException(401, "Token de webhook invalido")

    raw = await request.body()
    try:
        data = _json.loads(raw)
    except Exception:
        raise HTTPException(400, "Payload invalido")

    event_id = data.get("id")
    event_name = data.get("event", "")

    if not event_id:
        raise HTTPException(400, "Campo 'id' ausente no payload")

    # Idempotência
    if db.get(AsaasWebhookEvent, event_id):
        logging.info("[WEBHOOK] Evento duplicado ignorado event_id=%s", event_id)
        return {"ok": True, "duplicated": True}

    # Persiste o evento
    db.add(AsaasWebhookEvent(
        id=event_id,
        event=event_name,
        payload=raw.decode("utf-8"),
    ))

    # Atualiza a cobrança se o evento for mapeado
    payment = data.get("payment", {})
    external_ref = payment.get("externalReference")  # cobranca.id

    if event_name in _EVENTO_MAP and external_ref:
        novo_status, nova_fase, acao = _EVENTO_MAP[event_name]
        cobranca = db.query(Cobranca).filter_by(id=external_ref).first()
        if cobranca:
            status_anterior = cobranca.status
            cobranca.status = novo_status
            if nova_fase is not None:
                cobranca.fase_atual = nova_fase
            if novo_status == "pago":
                cobranca.data_pagamento = _now()
            cobranca.updated_at = _now()
            db.add(HistoricoCobranca(
                id=str(uuid.uuid4()),
                cobranca_id=cobranca.id,
                acao=acao,
                status_anterior=status_anterior,
                status_novo=novo_status,
                observacao=f"event_id={event_id} event={event_name}",
            ))
            logging.info(
                "[WEBHOOK] Cobranca atualizada cobranca_id=%s event=%s status=%s",
                cobranca.id, event_name, novo_status,
            )
        else:
            logging.warning("[WEBHOOK] Cobranca nao encontrada externalReference=%s", external_ref)
    else:
        logging.info("[WEBHOOK] Evento nao mapeado ignorado event=%s", event_name)

    db.commit()
    return {"ok": True}
