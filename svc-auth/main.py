import os, uuid, enum, hmac, logging
from datetime import datetime, timedelta
from fastapi import FastAPI, HTTPException, Depends, Header, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from pydantic import BaseModel, EmailStr
import bcrypt
from jose import jwt, JWTError
from sqlalchemy import create_engine, Column, String, Boolean, DateTime, Enum as SAEnum
from sqlalchemy.engine import URL, make_url
from sqlalchemy.orm import DeclarativeBase, Session, sessionmaker
from dotenv import load_dotenv

load_dotenv()

# ── Config ────────────────────────────────────────────────────────────────────

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

KEALEX_DATABASE_URL         = _get_database_url()
KEALEX_SECRET_KEY           = os.getenv("KEALEX_SECRET_KEY") or os.getenv("KEALEX_JWT_SECRET")
if not KEALEX_SECRET_KEY:
    raise RuntimeError("KEALEX_SECRET_KEY ou KEALEX_JWT_SECRET precisa estar configurada no ambiente")
ALGORITHM            = "HS256"
TOKEN_EXPIRE_MINUTES = 60 * 8
TRIAL_DAYS           = 7

engine       = create_engine(KEALEX_DATABASE_URL, pool_pre_ping=True, pool_recycle=280, pool_size=5, max_overflow=10)
SessionLocal = sessionmaker(bind=engine, autocommit=False, autoflush=False)
bearer       = HTTPBearer()

# ── Helpers ───────────────────────────────────────────────────────────────────

def _hash(p: str) -> str:
    return bcrypt.hashpw(p.encode(), bcrypt.gensalt()).decode()

def _verify(p: str, h: str) -> bool:
    try:
        return bcrypt.checkpw(p.encode(), h.encode())
    except Exception:
        return False

# ── Models ────────────────────────────────────────────────────────────────────

class Base(DeclarativeBase): pass

class RoleEnum(str, enum.Enum):
    admin    = "admin"
    advogado = "advogado"
    cliente  = "cliente"

class Tenant(Base):
    __tablename__ = "tenants"
    id               = Column(String(36),  primary_key=True, default=lambda: str(uuid.uuid4()))
    nome             = Column(String(255), nullable=False)
    slug             = Column(String(100), unique=True, nullable=False)
    plano            = Column(String(20),  nullable=False, default="trial")
    trial_started_at = Column(DateTime,    nullable=True)
    trial_expires_at = Column(DateTime,    nullable=True)
    asaas_customer_id = Column(String(80), nullable=True)
    billing_name = Column(String(255), nullable=True)
    billing_email = Column(String(255), nullable=True)
    billing_cpf_cnpj = Column(String(20), nullable=True)
    billing_phone = Column(String(30), nullable=True)
    billing_mobile_phone = Column(String(30), nullable=True)
    billing_postal_code = Column(String(10), nullable=True)
    billing_address = Column(String(255), nullable=True)
    billing_address_number = Column(String(20), nullable=True)
    billing_complement = Column(String(100), nullable=True)
    billing_neighborhood = Column(String(100), nullable=True)
    billing_city = Column(String(100), nullable=True)
    billing_state = Column(String(2), nullable=True)
    asaas_subscription_id = Column(String(80), nullable=True)
    subscription_plan = Column(String(20), nullable=True)
    subscription_status = Column(String(20), nullable=False, default="trialing")
    next_due_date = Column(String(10), nullable=True)
    ativo            = Column(Boolean,     default=True)
    created_at       = Column(DateTime,    default=datetime.utcnow)
    updated_at       = Column(DateTime,    default=datetime.utcnow, onupdate=datetime.utcnow)

class Usuario(Base):
    __tablename__ = "usuarios"
    id            = Column(String(36),  primary_key=True, default=lambda: str(uuid.uuid4()))
    tenant_id     = Column(String(36),  nullable=False)
    escritorio_id = Column(String(36),  nullable=True)
    nome          = Column(String(255), nullable=False)
    email         = Column(String(255), nullable=False)
    senha_hash    = Column(String(255), nullable=False)
    role          = Column(SAEnum(RoleEnum, name="role_enum_auth"), nullable=False)
    ativo         = Column(Boolean,     default=True)
    created_at    = Column(DateTime,    default=datetime.utcnow)
    updated_at    = Column(DateTime,    default=datetime.utcnow, onupdate=datetime.utcnow)

class AsaasWebhookEvent(Base):
    __tablename__ = "asaas_webhook_events"
    id = Column(String(100), primary_key=True)
    event = Column(String(80), nullable=False)
    received_at = Column(DateTime, default=datetime.utcnow, nullable=False)

# ── DB ────────────────────────────────────────────────────────────────────────

def get_db():
    db = SessionLocal()
    try:
        yield db
    except Exception:
        db.rollback()
        raise
    finally:
        db.close()

def _init_db():
    try:
        Base.metadata.create_all(engine)
        with SessionLocal() as db:
            tenant = db.query(Tenant).filter_by(slug="kealex").first()
            if not tenant:
                now = datetime.utcnow()
                tenant = Tenant(
                    nome="Kealex", slug="kealex", plano="trial",
                    trial_started_at=now,
                    trial_expires_at=now + timedelta(days=TRIAL_DAYS),
                )
                db.add(tenant)
                db.flush()
            else:
                # garante que tenants antigos tenham trial_started_at preenchido
                if tenant.trial_started_at is None and tenant.plano == "trial":
                    tenant.trial_started_at = tenant.created_at
                    tenant.trial_expires_at = tenant.created_at + timedelta(days=TRIAL_DAYS)
                    db.flush()

            admin = db.query(Usuario).filter_by(email="admin@kealex.com").first()
            if not admin:
                admin = Usuario(
                    tenant_id=tenant.id, nome="Admin Kealex",
                    email="admin@kealex.com", senha_hash=_hash("admin123"),
                    role=RoleEnum.admin,
                )
                db.add(admin)
            else:
                if not admin.tenant_id:
                    admin.tenant_id = tenant.id
                if not admin.senha_hash.startswith("$2b$"):
                    admin.senha_hash = _hash("admin123")
            db.commit()
    except Exception as e:
        print(f"[ERRO] Database init falhou: {type(e).__name__}: {e}")
        import traceback; traceback.print_exc()
        raise

# ── JWT ───────────────────────────────────────────────────────────────────────

def _make_token(user: Usuario) -> str:
    exp = datetime.utcnow() + timedelta(minutes=TOKEN_EXPIRE_MINUTES)
    return jwt.encode(
        {"sub": user.id, "role": user.role, "tenant_id": user.tenant_id, "exp": exp},
        KEALEX_SECRET_KEY, ALGORITHM,
    )

def verify_token(creds: HTTPAuthorizationCredentials = Depends(bearer)):
    try:
        return jwt.decode(creds.credentials, KEALEX_SECRET_KEY, algorithms=[ALGORITHM])
    except JWTError:
        raise HTTPException(401, "Token inválido")

# ── Trial guard ───────────────────────────────────────────────────────────────

def _check_tenant_access(tenant: Tenant | None, role: str) -> None:
    """Bloqueia rotas da plataforma sem bloquear o login ou a regularização."""
    if role == "admin":
        return
    if tenant is None:
        raise HTTPException(403, "Conta sem assinatura válida. Regularize o pagamento para continuar.")
    if not tenant.ativo:
        raise HTTPException(403, "Conta inativa. Regularize sua assinatura para continuar.")
    if tenant.plano == "trial" and not tenant.ativo:
        status = "inactive"
    elif tenant.plano == "trial":
        if tenant.trial_expires_at and datetime.utcnow() >= tenant.trial_expires_at:
            raise HTTPException(403, "Trial expirado. Assine um plano para continuar.")
        return
    if tenant.plano in ("starter", "professional", "enterprise") and tenant.subscription_status == "active":
        return
    raise HTTPException(403, "Assinatura pendente ou vencida. Regularize o pagamento para continuar.")

def require_active_trial(payload=Depends(verify_token), db: Session = Depends(get_db)):
    """Verifica acesso à plataforma; endpoints de cobrança usam verify_token."""
    tenant_id = payload.get("tenant_id")
    role      = payload.get("role", "")
    tenant    = db.query(Tenant).filter_by(id=tenant_id).first() if tenant_id else None
    _check_tenant_access(tenant, role)
    return payload

# ── App ───────────────────────────────────────────────────────────────────────

app = FastAPI(title="svc-auth")
app.add_middleware(CORSMiddleware, allow_origins=["*"], allow_methods=["*"], allow_headers=["*"])

@app.on_event("startup")
def startup_event():
    _init_db()

# ── Schemas ───────────────────────────────────────────────────────────────────

class LoginIn(BaseModel):
    email: EmailStr
    senha: str

class RegisterIn(BaseModel):
    nome:     str
    email:    EmailStr
    cpfCnpj:  str
    whatsapp: str
    perfil:   str = "advogado"  # advogado | escritorio | corporativo
    senha:    str | None = None  # opcional; se omitida, gera senha temporária

class AuthUser(BaseModel):
    id:                 str
    nome:               str
    email:              str
    role:               str
    tenantId:           str
    accessToken:        str
    plano:              str
    subscriptionStatus: str | None = None
    tenantAtivo:        bool = True
    trialStartedAt:     str | None = None
    trialExpiresAt:     str | None = None
    escritorioId:       str | None = None
    modalidade:         str | None = None  # autonomo | escritorio

# ── Endpoints ─────────────────────────────────────────────────────────────────

@app.post("/k1/lex/auth/register", response_model=AuthUser, status_code=201)
def register(body: RegisterIn, db: Session = Depends(get_db)):
    cpf_cnpj = _digits(body.cpfCnpj)
    if not cpf_cnpj or len(cpf_cnpj) not in (11, 14):
        raise HTTPException(400, "Informe um CPF ou CNPJ válido.")

    # e-mail já cadastrado?
    if db.query(Usuario).filter_by(email=body.email).first():
        raise HTTPException(409, "E-mail já cadastrado. Acesse /entrar para fazer login.")

    now   = datetime.utcnow()
    slug  = body.email.split("@")[0].lower().replace(".", "-")[:80]

    # garante slug único
    base_slug, counter = slug, 1
    while db.query(Tenant).filter_by(slug=slug).first():
        slug = f"{base_slug}-{counter}"
        counter += 1

    tenant = Tenant(
        nome=body.nome,
        slug=slug,
        plano="trial",
        trial_started_at=now,
        trial_expires_at=now + timedelta(days=TRIAL_DAYS),
        billing_cpf_cnpj=cpf_cnpj,
        billing_mobile_phone=_digits(body.whatsapp),
    )
    db.add(tenant)
    db.flush()  # gera tenant.id sem commit

    senha_final = body.senha if body.senha and len(body.senha) >= 6 else str(uuid.uuid4())[:8]
    user = Usuario(
        tenant_id=tenant.id,
        nome=body.nome,
        email=body.email,
        senha_hash=_hash(senha_final),
        role=RoleEnum.advogado,
    )
    db.add(user)
    db.commit()
    db.refresh(user)
    db.refresh(tenant)

    print(f"[REGISTER] novo trial: {body.email} | tenant={tenant.id}")

    return AuthUser(
        id=user.id,
        nome=user.nome,
        email=user.email,
        role=user.role,
        tenantId=tenant.id,
        accessToken=_make_token(user),
        plano=tenant.plano,
        subscriptionStatus=tenant.subscription_status,
        tenantAtivo=tenant.ativo,
        trialStartedAt=tenant.trial_started_at.isoformat(),
        trialExpiresAt=tenant.trial_expires_at.isoformat(),
        escritorioId=getattr(user, 'escritorio_id', None),
        modalidade="escritorio" if getattr(user, 'escritorio_id', None) else "autonomo",
    )


@app.post("/k1/lex/auth/login", response_model=AuthUser)
def login(body: LoginIn, db: Session = Depends(get_db)):
    user = db.query(Usuario).filter_by(email=body.email, ativo=True).first()
    if not user or not _verify(body.senha, user.senha_hash):
        raise HTTPException(401, "Credenciais inválidas")

    tenant = db.query(Tenant).filter_by(id=user.tenant_id).first()

    # Contas com trial vencido ainda podem autenticar para acessar a area de cobranca.

    return AuthUser(
        id=user.id,
        nome=user.nome,
        email=user.email,
        role=user.role,
        tenantId=user.tenant_id,
        accessToken=_make_token(user),
        plano=tenant.plano if tenant else "trial",
        subscriptionStatus=tenant.subscription_status if tenant else None,
        tenantAtivo=tenant.ativo if tenant else False,
        trialStartedAt=tenant.trial_started_at.isoformat() if tenant and tenant.trial_started_at else None,
        trialExpiresAt=tenant.trial_expires_at.isoformat() if tenant and tenant.trial_expires_at else None,
        escritorioId=getattr(user, 'escritorio_id', None),
        modalidade="escritorio" if getattr(user, 'escritorio_id', None) else "autonomo",
    )

@app.get("/k1/lex/auth/me")
def me(payload=Depends(require_active_trial)):
    return payload


# ── Pre-registro (fluxo de assinatura) ───────────────────────────────────────

class PreRegisterIn(BaseModel):
    nome:  str
    email: EmailStr
    senha: str

class PreRegisterOut(BaseModel):
    userId:   str
    tenantId: str
    token:    str  # token temporario para continuar o fluxo

@app.post("/k1/lex/auth/pre-register", response_model=PreRegisterOut, status_code=201)
def pre_register(body: PreRegisterIn, db: Session = Depends(get_db)):
    """Cria usuario INATIVO + tenant pendente. Ativado apos pagamento confirmado."""
    if len(body.senha) < 6:
        raise HTTPException(400, "Senha deve ter no minimo 6 caracteres")
    if db.query(Usuario).filter_by(email=body.email).first():
        raise HTTPException(409, "E-mail ja cadastrado. Acesse /entrar para fazer login.")

    slug = body.email.split("@")[0].lower().replace(".", "-")[:80]
    base_slug, counter = slug, 1
    while db.query(Tenant).filter_by(slug=slug).first():
        slug = f"{base_slug}-{counter}"
        counter += 1

    now = datetime.utcnow()
    tenant = Tenant(
        nome=body.nome, slug=slug,
        plano="trial",
        trial_started_at=now,
        trial_expires_at=now + timedelta(days=TRIAL_DAYS),
        ativo=True,
    )
    db.add(tenant)
    db.flush()

    user = Usuario(
        tenant_id=tenant.id, nome=body.nome, email=body.email,
        senha_hash=_hash(body.senha), role=RoleEnum.advogado,
        ativo=True,  # teste gratis liberado; billing valida o entitlement
    )
    db.add(user)
    db.commit()
    db.refresh(user)

    # token temporario para o fluxo de assinatura (nao passa pelo trial guard)
    token = jwt.encode(
        {"sub": user.id, "role": user.role, "tenant_id": tenant.id,
         "exp": datetime.utcnow() + timedelta(hours=2), "pre": True},
        KEALEX_SECRET_KEY, ALGORITHM,
    )
    print(f"[PRE-REGISTER] usuario inativo criado: {body.email} | tenant={tenant.id}")
    return PreRegisterOut(userId=user.id, tenantId=tenant.id, token=token)


@app.post("/k1/lex/auth/ativar", response_model=AuthUser)
def ativar_usuario(db: Session = Depends(get_db), payload=Depends(verify_token)):
    """Endpoint legado desativado: somente webhook autenticado altera entitlement."""
    raise HTTPException(410, "Ativacao manual desativada. Aguarde a confirmacao do pagamento.")


# ── Assinatura (Asaas) ────────────────────────────────────────────────────────

import httpx

KEALEX_ASAAS_API_KEY = os.getenv("KEALEX_ASAAS_API_KEY", "")
ASAAS_BASE    = os.getenv("KEALEX_ASAAS_BASE_URL", "").rstrip("/")
if not ASAAS_BASE:
    raise RuntimeError("KEALEX_ASAAS_BASE_URL precisa estar configurada no ambiente")

PLANOS = {
    "starter":      {"value": 197.00, "description": "Plano Starter"},
    "professional": {"value": 397.00, "description": "Plano Professional"},
}

class CreditCardIn(BaseModel):
    holderName:  str
    number:      str
    expiryMonth: str
    expiryYear:  str
    ccv:         str

class HolderInfoIn(BaseModel):
    name:              str
    email:             str
    cpfCnpj:           str
    postalCode:        str
    addressNumber:     str
    addressComplement: str | None = None
    phone:             str | None = None
    mobilePhone:       str | None = None
    address:           str | None = None
    neighborhood:      str | None = None
    city:              str | None = None
    state:             str | None = None


def _digits(value: str | None) -> str | None:
    if value is None:
        return None
    return "".join(character for character in value if character.isdigit())

def _is_luhn_valid(number: str) -> bool:
    checksum = 0
    parity = len(number) % 2
    for index, character in enumerate(number):
        digit = int(character)
        if index % 2 == parity:
            digit *= 2
            if digit > 9:
                digit -= 9
        checksum += digit
    return checksum % 10 == 0

class AssinarIn(BaseModel):
    plano:           str
    periodicidade:   str = "mensal"   # mensal | trimestral
    asaasCustomerId: str
    creditCard:      CreditCardIn
    holderInfo:      HolderInfoIn
    remoteIp:        str

class AssinarOut(BaseModel):
    subscriptionId: str
    plano:          str
    periodicidade:  str
    status:         str
    nextDueDate:    str
    value:          float
    valorMensal:    float
    desconto:       float

def _build_asaas_card_payload(body: AssinarIn) -> dict:
    """Normaliza os dados de cartão e titular aceitos pelo Asaas."""
    holder = body.holderInfo
    card_number = _digits(body.creditCard.number) or ""
    if not 13 <= len(card_number) <= 19 or not _is_luhn_valid(card_number):
        raise HTTPException(400, "Número do cartão inválido. Confira os dígitos informados.")

    mobile_phone = _digits(holder.mobilePhone)
    holder_info = {
        "name": holder.name,
        "email": holder.email,
        "cpfCnpj": _digits(holder.cpfCnpj),
        "postalCode": _digits(holder.postalCode),
        "addressNumber": holder.addressNumber,
        "addressComplement": holder.addressComplement,
        "phone": _digits(holder.phone) or mobile_phone,
        # mobilePhone é aceito pelo endpoint de assinatura do Asaas.
        "mobilePhone": mobile_phone,
    }

    return {
        "creditCard": {
            "holderName": body.creditCard.holderName,
            "number": card_number,
            "expiryMonth": body.creditCard.expiryMonth,
            "expiryYear": body.creditCard.expiryYear,
            "ccv": body.creditCard.ccv,
        },
        "creditCardHolderInfo": {
            key: value for key, value in holder_info.items()
            if value not in (None, "")
        },
        "remoteIp": body.remoteIp,
    }

def _build_asaas_subscription_payload(body: AssinarIn, plan_cfg: dict, next_due: str,
                                      value: float, cycle: str) -> dict:
    """Converte o payload interno para o formato de POST /v3/subscriptions."""
    return {
        "customer": body.asaasCustomerId,
        "billingType": "CREDIT_CARD",
        "value": value,
        "nextDueDate": next_due,
        "cycle": cycle,
        "description": plan_cfg["description"],
        **_build_asaas_card_payload(body),
    }

@app.post("/k1/lex/auth/assinar", response_model=AssinarOut)
def assinar(body: AssinarIn, db: Session = Depends(get_db), payload=Depends(verify_token)):
    plano_cfg = PLANOS.get(body.plano)
    if not plano_cfg:
        raise HTTPException(400, f"Plano invalido: {body.plano}. Use: {list(PLANOS.keys())}")

    tenant_id = payload.get("tenant_id")
    tenant = db.query(Tenant).filter_by(id=tenant_id).first()
    if not tenant:
        raise HTTPException(404, "Tenant nao encontrado")
    user = db.query(Usuario).filter_by(id=payload.get("sub"), tenant_id=tenant_id).first()
    if not user or (not user.ativo and payload.get("pre") is not True):
        raise HTTPException(403, "Sessao nao autorizada para contratar")
    if tenant.asaas_customer_id != body.asaasCustomerId:
        raise HTTPException(403, "Cliente Asaas nao vinculado a esta conta")
    periodicidade = body.periodicidade or "mensal"
    if periodicidade not in ("mensal", "trimestral"):
        raise HTTPException(400, "Periodicidade invalida. Use mensal ou trimestral.")
    if tenant.asaas_subscription_id and tenant.subscription_status == "active":
        raise HTTPException(409, "Ja existe uma assinatura vinculada a esta conta")

    meses = 3 if periodicidade == "trimestral" else 1
    desconto = plano_cfg["value"] * meses * 0.05 if periodicidade == "trimestral" else 0.0
    valor_total = round(plano_cfg["value"] * meses - desconto, 2)
    cycle = "QUARTERLY" if periodicidade == "trimestral" else "MONTHLY"

    now = datetime.utcnow()
    if tenant.plano == "trial" and tenant.trial_expires_at and tenant.trial_expires_at > now:
        next_due = tenant.trial_expires_at.strftime("%Y-%m-%d")
    else:
        next_due = (now + timedelta(days=1)).strftime("%Y-%m-%d")

    headers = {
        "access_token": KEALEX_ASAAS_API_KEY,
        "Content-Type": "application/json",
        "User-Agent": "Kealex/1.0.0",
    }

    # Se já existe uma assinatura pendente, substitui-a antes de criar outra.
    # A remoção pelo Asaas também remove cobranças pendentes e vencidas ligadas a ela.
    if tenant.asaas_subscription_id and tenant.subscription_status == "pending":
        previous_subscription_id = tenant.asaas_subscription_id
        try:
            payments_resp = httpx.get(
                f"{ASAAS_BASE}/payments",
                params={"subscription": previous_subscription_id, "limit": 100},
                headers=headers,
                timeout=15,
            )
            if payments_resp.status_code != 200:
                raise HTTPException(502, "Nao foi possivel verificar a assinatura pendente no Asaas.")

            payments = payments_resp.json().get("data", [])
            if any((payment.get("status") or "").upper() in {"CONFIRMED", "RECEIVED"} for payment in payments):
                tenant.subscription_status = "active"
                tenant.plano = tenant.subscription_plan or tenant.plano
                tenant.ativo = True
                tenant.updated_at = datetime.utcnow()
                db.query(Usuario).filter_by(tenant_id=tenant.id).update({"ativo": True})
                db.commit()
                raise HTTPException(409, "A assinatura anterior ja possui pagamento confirmado.")

            remove_resp = httpx.delete(
                f"{ASAAS_BASE}/subscriptions/{previous_subscription_id}",
                headers=headers,
                timeout=60,
            )
            if remove_resp.status_code not in (200, 204, 404):
                detail = remove_resp.json().get("errors", remove_resp.text)
                raise HTTPException(502, f"Nao foi possivel substituir a assinatura pendente: {detail}")
            logging.info(
                "[ASSINAR] Assinatura pendente removida para substituicao tenant=%s subscription=%s",
                tenant.id,
                previous_subscription_id,
            )
        except httpx.TimeoutException:
            raise HTTPException(504, "Timeout ao substituir a assinatura pendente no Asaas.")

    # Retry the existing overdue invoice instead of creating a second subscription.
    if tenant.subscription_status == "past_due" and tenant.asaas_subscription_id:
        if body.plano != tenant.subscription_plan:
            raise HTTPException(409, "Para regularizar a cobrança, selecione o plano atual da conta.")
        try:
            payments_response = httpx.get(
                f"{ASAAS_BASE}/payments",
                params={"subscription": tenant.asaas_subscription_id, "limit": 100},
                headers=headers,
                timeout=15,
            )
            if payments_response.status_code != 200:
                raise HTTPException(502, "Nao foi possivel consultar a cobranca vencida no Asaas.")
            overdue_payments = [
                payment for payment in payments_response.json().get("data", [])
                if payment.get("status") == "OVERDUE"
            ]
            if not overdue_payments:
                raise HTTPException(409, "Nao encontramos uma cobranca vencida para regularizar no Asaas.")
            overdue_payments.sort(key=lambda payment: payment.get("dueDate", ""), reverse=True)
            payment = overdue_payments[0]
            payment_resp = httpx.post(
                f"{ASAAS_BASE}/payments/{payment['id']}/payWithCreditCard",
                json=_build_asaas_card_payload(body),
                headers=headers,
                timeout=60,
            )
            if payment_resp.status_code != 200:
                detail = payment_resp.json().get("errors", payment_resp.text)
                raise HTTPException(422, f"Asaas recusou a regularizacao: {detail}")
            payment_data = payment_resp.json()
        except httpx.TimeoutException:
            raise HTTPException(504, "Timeout ao regularizar a cobranca no Asaas.")

        payment_status = (payment_data.get("status") or "").upper()
        if payment_status in ("CONFIRMED", "RECEIVED"):
            tenant.subscription_status = "active"
            tenant.plano = tenant.subscription_plan or body.plano
            tenant.ativo = True
            db.query(Usuario).filter_by(tenant_id=tenant.id).update({"ativo": True})
        elif payment_status in ("PENDING", "AWAITING_RISK_ANALYSIS"):
            tenant.subscription_status = "pending"
        tenant.next_due_date = payment_data.get("dueDate") or tenant.next_due_date
        tenant.updated_at = datetime.utcnow()
        db.commit()
        return AssinarOut(
            subscriptionId=tenant.asaas_subscription_id,
            plano=tenant.subscription_plan or body.plano,
            periodicidade=periodicidade,
            status=payment_status or "PENDING",
            nextDueDate=tenant.next_due_date or next_due,
            value=float(payment_data.get("value") or valor_total),
            valorMensal=plano_cfg["value"],
            desconto=desconto,
        )

    # Create the recurring subscription first so every payment, including an
    # asynchronous card confirmation, is associated with the webhook's subscription ID.
    try:
        sub_resp = httpx.post(
            f"{ASAAS_BASE}/subscriptions",
            json=_build_asaas_subscription_payload(body, plano_cfg, next_due, valor_total, cycle),
            headers=headers,
            timeout=60,
        )
        if sub_resp.status_code not in (200, 201):
            detail = sub_resp.json().get("errors", sub_resp.text)
            raise HTTPException(422, f"Asaas recusou a assinatura: {detail}")
        subscription = sub_resp.json()
    except httpx.TimeoutException:
        raise HTTPException(504, "Timeout ao criar assinatura no Asaas.")

    subscription_id = subscription.get("id")
    if not subscription_id:
        raise HTTPException(502, "Asaas criou uma resposta sem identificador de assinatura.")

    # Salva como pending e aguarda webhook para ativar — não polling de status
    tenant.asaas_subscription_id = subscription_id
    tenant.subscription_plan = body.plano
    tenant.subscription_status = "pending"
    tenant.next_due_date = subscription.get("nextDueDate") or next_due
    tenant.updated_at = datetime.utcnow()
    db.commit()

    return AssinarOut(
        subscriptionId=subscription_id,
        plano=body.plano,
        periodicidade=periodicidade,
        status="PENDING",
        nextDueDate=tenant.next_due_date,
        value=valor_total,
        valorMensal=plano_cfg["value"],
        desconto=desconto,
    )


class AssinarPixIn(BaseModel):
    plano:           str
    periodicidade:   str = "mensal"
    asaasCustomerId: str

class AssinarPixOut(BaseModel):
    subscriptionId: str
    plano:          str
    periodicidade:  str
    status:         str
    nextDueDate:    str
    value:          float
    valorMensal:    float
    desconto:       float
    pixQrCode:      str   # base64 PNG do QR Code
    pixKey:         str   # payload copia-e-cola
    pixExpiresAt:   str   # ISO datetime de expiração

@app.post("/k1/lex/auth/assinar-pix", response_model=AssinarPixOut)
def assinar_pix(body: AssinarPixIn, db: Session = Depends(get_db), payload=Depends(verify_token)):
    plano_cfg = PLANOS.get(body.plano)
    if not plano_cfg:
        raise HTTPException(400, f"Plano invalido: {body.plano}")
    periodicidade = body.periodicidade or "mensal"
    if periodicidade not in ("mensal", "trimestral"):
        raise HTTPException(400, "Periodicidade invalida. Use mensal ou trimestral.")

    tenant_id = payload.get("tenant_id")
    tenant = db.query(Tenant).filter_by(id=tenant_id).first()
    if not tenant:
        raise HTTPException(404, "Tenant nao encontrado")
    if tenant.asaas_customer_id != body.asaasCustomerId:
        raise HTTPException(403, "Cliente Asaas nao vinculado a esta conta")
    if tenant.asaas_subscription_id and tenant.subscription_status in ("pending", "active"):
        raise HTTPException(409, "Ja existe uma assinatura vinculada a esta conta")

    meses = 3 if periodicidade == "trimestral" else 1
    desconto = plano_cfg["value"] * meses * 0.05 if periodicidade == "trimestral" else 0.0
    valor_total = round(plano_cfg["value"] * meses - desconto, 2)
    cycle = "QUARTERLY" if periodicidade == "trimestral" else "MONTHLY"
    now = datetime.utcnow()
    if tenant.plano == "trial" and tenant.trial_expires_at and tenant.trial_expires_at > now:
        next_due = tenant.trial_expires_at.strftime("%Y-%m-%d")
    else:
        next_due = (now + timedelta(days=1)).strftime("%Y-%m-%d")

    headers = {"access_token": KEALEX_ASAAS_API_KEY, "Content-Type": "application/json", "User-Agent": "Kealex/1.0.0"}

    if tenant.subscription_status == "past_due" and tenant.asaas_subscription_id:
        if body.plano != tenant.subscription_plan:
            raise HTTPException(409, "Para regularizar a cobranca, selecione o plano atual da conta.")
        try:
            payments_resp = httpx.get(
                f"{ASAAS_BASE}/payments",
                params={"subscription": tenant.asaas_subscription_id, "limit": 100},
                headers=headers,
                timeout=15,
            )
            if payments_resp.status_code != 200:
                raise HTTPException(502, "Nao foi possivel consultar a cobranca vencida no Asaas.")
            overdue_payments = [
                payment for payment in payments_resp.json().get("data", [])
                if payment.get("status") == "OVERDUE" and payment.get("billingType") == "PIX"
            ]
            if not overdue_payments:
                raise HTTPException(409, "Esta cobranca vencida nao aceita PIX. Escolha cartao de credito.")
            overdue_payments.sort(key=lambda payment: payment.get("dueDate", ""), reverse=True)
            payment_id = overdue_payments[0]["id"]
            due_date = overdue_payments[0].get("dueDate") or next_due
            qr_resp = httpx.get(
                f"{ASAAS_BASE}/payments/{payment_id}/pixQrCode",
                headers=headers,
                timeout=15,
            )
            if qr_resp.status_code != 200:
                raise HTTPException(422, f"Nao foi possivel recuperar o PIX vencido: {qr_resp.text}")
            qr_data = qr_resp.json()
        except httpx.TimeoutException:
            raise HTTPException(504, "Timeout ao consultar a cobranca PIX no Asaas.")

        return AssinarPixOut(
            subscriptionId=tenant.asaas_subscription_id,
            plano=tenant.subscription_plan or body.plano,
            periodicidade=periodicidade,
            status="PENDING",
            nextDueDate=due_date,
            value=float(overdue_payments[0].get("value") or valor_total),
            valorMensal=plano_cfg["value"],
            desconto=desconto,
            pixQrCode=qr_data.get("encodedImage", ""),
            pixKey=qr_data.get("payload", ""),
            pixExpiresAt=qr_data.get("expirationDate") or (now + timedelta(hours=24)).isoformat(),
        )

    # 1. Criar assinatura PIX
    try:
        resp = httpx.post(
            f"{ASAAS_BASE}/subscriptions",
            json={
                "customer":    body.asaasCustomerId,
                "billingType": "PIX",
                "nextDueDate": next_due,
                "value":       valor_total,
                "cycle":       cycle,
                "description": plano_cfg["description"],
            },
            headers=headers,
            timeout=20,
        )
        if resp.status_code not in (200, 201):
            raise HTTPException(422, f"Asaas recusou: {resp.json().get('errors', resp.text)}")
        sub = resp.json()
        subscription_id = sub.get("id")
        if not subscription_id:
            raise HTTPException(502, "Asaas criou uma resposta sem identificador de assinatura.")
    except httpx.TimeoutException:
        raise HTTPException(504, "Timeout ao conectar com Asaas")

    tenant.asaas_subscription_id = subscription_id
    tenant.subscription_plan = body.plano
    tenant.subscription_status = "pending"
    tenant.next_due_date = next_due
    tenant.ativo = True
    tenant.updated_at = datetime.utcnow()
    db.commit()

    # 2. Buscar o pagamento gerado para a assinatura
    try:
        resp = httpx.get(
            f"{ASAAS_BASE}/payments",
            params={"subscription": subscription_id, "limit": 1},
            headers=headers,
            timeout=15,
        )
        if resp.status_code != 200:
            raise HTTPException(502, "Nao foi possivel consultar a primeira cobranca PIX no Asaas.")
        payments = resp.json().get("data", [])
        if not payments:
            raise HTTPException(422, "Nenhum pagamento gerado para a assinatura PIX")
        payment_id = payments[0]["id"]
        due_date = payments[0].get("dueDate", next_due)
    except httpx.TimeoutException:
        raise HTTPException(504, "Timeout ao buscar pagamento")

    # 3. Buscar QR Code PIX do pagamento
    try:
        resp = httpx.get(
            f"{ASAAS_BASE}/payments/{payment_id}/pixQrCode",
            headers=headers,
            timeout=15,
        )
        if resp.status_code != 200:
            raise HTTPException(422, f"Erro ao obter QR Code PIX: {resp.text}")
        qr_data = resp.json()
    except httpx.TimeoutException:
        raise HTTPException(504, "Timeout ao obter QR Code PIX")

    tenant.next_due_date = due_date
    tenant.updated_at = datetime.utcnow()
    db.commit()

    expires_at = (now + timedelta(hours=24)).isoformat()

    return AssinarPixOut(
        subscriptionId=subscription_id,
        plano=body.plano,
        periodicidade=periodicidade,
        status="PENDING",
        nextDueDate=due_date,
        value=valor_total,
        valorMensal=plano_cfg["value"],
        desconto=desconto,
        pixQrCode=qr_data.get("encodedImage", ""),
        pixKey=qr_data.get("payload", ""),
        pixExpiresAt=qr_data.get("expirationDate") or expires_at,
    )


@app.post("/k1/lex/auth/criar-cliente-asaas")
def criar_cliente_asaas(body: HolderInfoIn, db: Session = Depends(get_db), payload=Depends(verify_token)):
    """Cria ou recupera um customer no Asaas para o usuario autenticado."""
    tenant = db.query(Tenant).filter_by(id=payload.get("tenant_id")).first()
    if not tenant:
        raise HTTPException(404, "Tenant nao encontrado")
    customer_data = {
        "name": body.name,
        "email": body.email,
        "cpfCnpj": _digits(body.cpfCnpj),
        "phone": _digits(body.phone),
        "mobilePhone": _digits(body.mobilePhone),
        "postalCode": _digits(body.postalCode),
        "addressNumber": body.addressNumber,
        "complement": body.addressComplement,
        "address": body.address,
        "province": body.neighborhood,
        "city": body.city,
    }
    customer_data = {key: value for key, value in customer_data.items() if value not in (None, "")}
    try:
        if tenant.asaas_customer_id:
            resp = httpx.put(
                f"{ASAAS_BASE}/customers/{tenant.asaas_customer_id}",
                json=customer_data,
                headers={"access_token": KEALEX_ASAAS_API_KEY, "Content-Type": "application/json"},
                timeout=15,
            )
        else:
            resp = httpx.post(
                f"{ASAAS_BASE}/customers",
                json=customer_data,
                headers={"access_token": KEALEX_ASAAS_API_KEY, "Content-Type": "application/json"},
                timeout=15,
            )
        if resp.status_code not in (200, 201):
            detail = resp.json().get("errors", resp.text)
            raise HTTPException(422, f"Asaas recusou os dados do titular: {detail}")
        customer_id = tenant.asaas_customer_id or resp.json().get("id")
        tenant.asaas_customer_id = customer_id
        tenant.billing_name = body.name
        tenant.billing_email = body.email
        tenant.billing_cpf_cnpj = _digits(body.cpfCnpj)
        tenant.billing_phone = _digits(body.phone)
        tenant.billing_mobile_phone = _digits(body.mobilePhone)
        tenant.billing_postal_code = _digits(body.postalCode)
        tenant.billing_address = body.address
        tenant.billing_address_number = body.addressNumber
        tenant.billing_complement = body.addressComplement
        tenant.billing_neighborhood = body.neighborhood
        tenant.billing_city = body.city
        tenant.billing_state = body.state
        db.commit()
        return {"customerId": customer_id}
    except httpx.TimeoutException:
        raise HTTPException(504, "Timeout ao conectar com Asaas")


@app.get("/k1/lex/auth/billing-profile")
def billing_profile(db: Session = Depends(get_db), payload=Depends(verify_token)):
    tenant = db.query(Tenant).filter_by(id=payload.get("tenant_id")).first()
    if not tenant:
        raise HTTPException(404, "Tenant nao encontrado")

    cpf_cnpj = tenant.billing_cpf_cnpj
    phone = tenant.billing_phone
    mobile_phone = tenant.billing_mobile_phone
    if tenant.asaas_customer_id and (not cpf_cnpj or (not phone and not mobile_phone)):
        try:
            response = httpx.get(
                f"{ASAAS_BASE}/customers/{tenant.asaas_customer_id}",
                headers={"access_token": KEALEX_ASAAS_API_KEY},
                timeout=10,
            )
            if response.status_code == 200:
                customer = response.json()
                cpf_cnpj = cpf_cnpj or customer.get("cpfCnpj")
                phone = phone or customer.get("phone")
                mobile_phone = mobile_phone or customer.get("mobilePhone")
                tenant.billing_cpf_cnpj = cpf_cnpj
                tenant.billing_phone = phone
                tenant.billing_mobile_phone = mobile_phone
                db.commit()
        except httpx.TimeoutException:
            pass

    return {
        "name": tenant.billing_name or "",
        "email": tenant.billing_email or "",
        "cpfCnpj": cpf_cnpj or "",
        "phone": phone or "",
        "mobilePhone": mobile_phone or "",
        "postalCode": tenant.billing_postal_code or "",
        "address": tenant.billing_address or "",
        "addressNumber": tenant.billing_address_number or "",
        "addressComplement": tenant.billing_complement or "",
        "neighborhood": tenant.billing_neighborhood or "",
        "city": tenant.billing_city or "",
        "state": tenant.billing_state or "",
    }


@app.post("/k1/lex/auth/asaas-webhook")
async def asaas_webhook(
    request: Request,
    db: Session = Depends(get_db),
    access_token: str | None = Header(default=None, alias="asaas-access-token"),
):
    expected = os.getenv("KEALEX_ASAAS_WEBHOOK_TOKEN", "")
    if not expected or not access_token or not hmac.compare_digest(access_token, expected):
        raise HTTPException(401, "Webhook nao autenticado")

    event = await request.json()
    event_id = event.get("id")
    event_name = event.get("event", "")
    if not event_id:
        raise HTTPException(400, "Evento sem identificador")
    if db.get(AsaasWebhookEvent, event_id):
        return {"ok": True, "duplicate": True}

    payment = event.get("payment") or {}
    subscription_id = payment.get("subscription") or (event.get("subscription") or {}).get("id")
    if not subscription_id:
        return {"ok": True, "ignored": True}
    tenant = db.query(Tenant).filter_by(asaas_subscription_id=subscription_id).with_for_update().first()
    db.add(AsaasWebhookEvent(id=event_id, event=event_name))
    if tenant:
        if event_name in ("PAYMENT_CONFIRMED", "PAYMENT_RECEIVED"):
            tenant.subscription_status = "active"
            tenant.plano = tenant.subscription_plan or tenant.plano
            tenant.ativo = True
            tenant.next_due_date = payment.get("dueDate") or tenant.next_due_date
            db.query(Usuario).filter_by(tenant_id=tenant.id).update({"ativo": True})
        elif event_name == "PAYMENT_OVERDUE":
            tenant.subscription_status = "past_due"
            tenant.ativo = False
        elif event_name == "SUBSCRIPTION_DELETED":
            tenant.subscription_status = "canceled"
            tenant.ativo = False
        tenant.updated_at = datetime.utcnow()
    db.commit()
    return {"ok": True, "ignored": tenant is None}

@app.get("/k1/lex/auth/billing-status")
def billing_status(db: Session = Depends(get_db), payload=Depends(verify_token)):
    tenant = db.query(Tenant).filter_by(id=payload.get("tenant_id")).first()
    if not tenant:
        raise HTTPException(404, "Tenant nao encontrado")
    now = datetime.utcnow()
    if tenant.plano == "trial":
        trial_expired = tenant.trial_expires_at and tenant.trial_expires_at <= now
        if tenant.subscription_status == "pending" and trial_expired:
            status = "pending"
        else:
            status = "trial_expired" if trial_expired else "trial"
    elif tenant.plano in ("starter", "professional", "enterprise"):
        subscription_status = (tenant.subscription_status or "").lower()
        if subscription_status in ("pending", "past_due", "canceled"):
            status = subscription_status
        elif tenant.ativo and subscription_status == "active":
            status = "active"
        else:
            status = "inactive"
    else:
        status = "inactive"
    return {
        "plano": tenant.plano,
        "status": status,
        "subscriptionStatus": tenant.subscription_status,
        "nextDueDate": tenant.next_due_date,
        "trialExpiresAt": tenant.trial_expires_at.isoformat() if tenant.trial_expires_at else None,
    }


@app.post("/k1/lex/auth/assinatura/reativar", response_model=AssinarOut)
def reativar_assinatura(body: dict = {}, db: Session = Depends(get_db), payload=Depends(verify_token)):
    """Verifica o status do pagamento pendente no Asaas e atualiza o tenant."""
    tenant = db.query(Tenant).filter_by(id=payload.get("tenant_id")).first()
    if not tenant or not tenant.asaas_subscription_id:
        raise HTTPException(404, "Nenhuma assinatura encontrada")
    if tenant.subscription_status == "active":
        raise HTTPException(409, "Assinatura ja esta ativa")

    headers = {"access_token": KEALEX_ASAAS_API_KEY, "Content-Type": "application/json", "User-Agent": "Kealex/1.0.0"}
    try:
        resp = httpx.get(
            f"{ASAAS_BASE}/payments",
            params={"subscription": tenant.asaas_subscription_id, "limit": 1},
            headers=headers,
            timeout=15,
        )
        payments = resp.json().get("data", []) if resp.status_code == 200 else []
        if not payments:
            raise HTTPException(422, "Nenhum pagamento encontrado para reativar")
        payment = payments[0]
        payment_status = (payment.get("status") or "").upper()
        plano_cfg = PLANOS.get(tenant.subscription_plan or tenant.plano, {})
        now = datetime.utcnow()
        if payment_status in ("CONFIRMED", "RECEIVED"):
            tenant.subscription_status = "active"
            tenant.plano = tenant.subscription_plan or tenant.plano
            tenant.ativo = True
            db.query(Usuario).filter_by(tenant_id=tenant.id).update({"ativo": True})
            db.commit()
        return AssinarOut(
            subscriptionId=tenant.asaas_subscription_id,
            plano=tenant.subscription_plan or tenant.plano,
            periodicidade="mensal",
            status=payment_status or "PENDING",
            nextDueDate=payment.get("dueDate") or now.strftime("%Y-%m-%d"),
            value=payment.get("value") or plano_cfg.get("value", 0),
            valorMensal=plano_cfg.get("value", 0),
            desconto=0.0,
        )
    except httpx.TimeoutException:
        raise HTTPException(504, "Timeout ao conectar com Asaas")


@app.get("/k1/lex/auth/assinatura")
def get_assinatura(db: Session = Depends(get_db), payload=Depends(verify_token)):
    tenant = db.query(Tenant).filter_by(id=payload.get("tenant_id")).first()
    if not tenant or not tenant.asaas_subscription_id:
        raise HTTPException(404, "Nenhuma assinatura encontrada")

    periodicidade = "mensal"
    pix_qr_code = None
    pix_key = None
    pix_expires_at = None
    billing_type = None

    # Tenta buscar detalhes atualizados no Asaas
    try:
        headers = {"access_token": KEALEX_ASAAS_API_KEY, "User-Agent": "Kealex/1.0.0"}
        resp = httpx.get(
            f"{ASAAS_BASE}/subscriptions/{tenant.asaas_subscription_id}",
            headers=headers,
            timeout=10,
        )
        if resp.status_code == 200:
            sub = resp.json()
            cycle = (sub.get("cycle") or "").upper()
            periodicidade = "trimestral" if cycle == "QUARTERLY" else "mensal"

        # Se pendente, tenta buscar QR Code do pagamento mais recente
        if tenant.subscription_status in ("pending", "past_due"):
            pay_resp = httpx.get(
                f"{ASAAS_BASE}/payments",
                params={"subscription": tenant.asaas_subscription_id, "limit": 100},
                headers=headers,
                timeout=10,
            )
            if pay_resp.status_code == 200:
                payments = [
                    payment for payment in pay_resp.json().get("data", [])
                    if payment.get("status") in ("PENDING", "OVERDUE")
                ]
                if payments:
                    payments.sort(key=lambda payment: payment.get("dueDate", ""), reverse=True)
                    payment = payments[0]
                    billing_type = (payment.get("billingType") or "").upper()
                    if billing_type == "PIX":
                        qr_resp = httpx.get(
                            f"{ASAAS_BASE}/payments/{payment['id']}/pixQrCode",
                            headers=headers,
                            timeout=10,
                        )
                        if qr_resp.status_code == 200:
                            qr = qr_resp.json()
                            pix_qr_code = qr.get("encodedImage")
                            pix_key = qr.get("payload")
                            pix_expires_at = qr.get("expirationDate")
    except httpx.TimeoutException:
        pass

    plano_cfg = PLANOS.get(tenant.subscription_plan or tenant.plano, {})
    return {
        "subscriptionId": tenant.asaas_subscription_id,
        "plano": tenant.subscription_plan or tenant.plano,
        "periodicidade": periodicidade,
        "valor": plano_cfg.get("value", 0),
        "status": tenant.subscription_status or "inactive",
        "subscriptionStatus": tenant.subscription_status or "pending",
        "billingType": billing_type,
        "createdAt": tenant.created_at.isoformat() if tenant.created_at else None,
        "nextDueDate": tenant.next_due_date,
        "pixQrCode": pix_qr_code,
        "pixKey": pix_key,
        "pixExpiresAt": pix_expires_at,
    }
@app.get("/health")
def health_simple():
    return {"status": "healthy", "service": "svc-auth"}

@app.get("/k1/lex/health")
def health():
    return {"status": "ok", "service": "svc-auth"}
