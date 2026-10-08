import os, uuid, enum, hmac
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
    billing_cpf_cnpj = Column(String(20), nullable=True)
    billing_phone = Column(String(30), nullable=True)
    billing_mobile_phone = Column(String(30), nullable=True)
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

def _check_trial(tenant: Tenant | None, role: str) -> None:
    """Lança 403 se o tenant está em trial expirado. Admin nunca é bloqueado."""
    if role == "admin":
        return
    if tenant is None:
        return
    if tenant.plano != "trial":
        return
    if tenant.trial_expires_at and datetime.utcnow() > tenant.trial_expires_at:
        raise HTTPException(403, "Trial expirado. Assine um plano para continuar.")

def require_active_trial(payload=Depends(verify_token), db: Session = Depends(get_db)):
    """Dependência reutilizável: verifica token + trial ativo."""
    tenant_id = payload.get("tenant_id")
    role      = payload.get("role", "")
    tenant    = db.query(Tenant).filter_by(id=tenant_id).first() if tenant_id else None
    _check_trial(tenant, role)
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
    id:             str
    nome:           str
    email:          str
    role:           str
    tenantId:       str
    accessToken:    str
    plano:          str
    trialStartedAt: str | None = None
    trialExpiresAt: str | None = None
    escritorioId:   str | None = None
    modalidade:     str | None = None  # autonomo | escritorio

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


def _digits(value: str | None) -> str | None:
    if value is None:
        return None
    return "".join(character for character in value if character.isdigit())

class AssinarIn(BaseModel):
    plano:          str          # starter | professional
    asaasCustomerId: str         # cus_xxx criado previamente no Asaas
    creditCard:     CreditCardIn
    holderInfo:     HolderInfoIn
    remoteIp:       str = "127.0.0.1"

class AssinarOut(BaseModel):
    subscriptionId: str
    plano:          str
    status:         str
    nextDueDate:    str
    value:          float

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
    if tenant.asaas_subscription_id and tenant.subscription_status in ("pending", "active", "past_due"):
        raise HTTPException(409, "Ja existe uma assinatura vinculada a esta conta")

    # Calcula nextDueDate: se ainda em trial, agenda para o fim do trial
    now = datetime.utcnow()
    if tenant.plano == "trial" and tenant.trial_expires_at and tenant.trial_expires_at > now:
        next_due = tenant.trial_expires_at.strftime("%Y-%m-%d")
    else:
        next_due = (now + timedelta(days=1)).strftime("%Y-%m-%d")

    payload_asaas = {
        "customer":    body.asaasCustomerId,
        "billingType": "CREDIT_CARD",
        "nextDueDate": next_due,
        "value":       plano_cfg["value"],
        "cycle":       "MONTHLY",
        "description": plano_cfg["description"],
        "creditCard": {
            "holderName":  body.creditCard.holderName,
            "number":      body.creditCard.number,
            "expiryMonth": body.creditCard.expiryMonth,
            "expiryYear":  body.creditCard.expiryYear,
            "ccv":         body.creditCard.ccv,
        },
        "creditCardHolderInfo": {
            "name":               body.holderInfo.name,
            "email":              body.holderInfo.email,
            "cpfCnpj":            _digits(body.holderInfo.cpfCnpj),
            "postalCode":         body.holderInfo.postalCode,
            "addressNumber":      body.holderInfo.addressNumber,
            "addressComplement":  body.holderInfo.addressComplement,
            "phone":              _digits(body.holderInfo.phone),
            "mobilePhone":        _digits(body.holderInfo.mobilePhone),
        },
        "remoteIp": body.remoteIp,
    }

    try:
        resp = httpx.post(
            f"{ASAAS_BASE}/subscriptions",
            json=payload_asaas,
            headers={"access_token": KEALEX_ASAAS_API_KEY, "Content-Type": "application/json"},
            timeout=20,
        )
        if resp.status_code not in (200, 201):
            detail = resp.json().get("errors", resp.text)
            raise HTTPException(422, f"Asaas recusou: {detail}")
        data = resp.json()
    except httpx.TimeoutException:
        raise HTTPException(504, "Timeout ao conectar com Asaas")

    # A criacao nao prova que a primeira cobranca foi liquidada.
    tenant.asaas_subscription_id = data.get("id")
    tenant.subscription_plan = body.plano
    tenant.subscription_status = "pending"
    tenant.next_due_date = data.get("nextDueDate", next_due)
    tenant.updated_at = datetime.utcnow()
    db.commit()

    return AssinarOut(
        subscriptionId=data.get("id", ""),
        plano=body.plano,
        status="PENDING_PAYMENT",
        nextDueDate=data.get("nextDueDate", next_due),
        value=plano_cfg["value"],
    )


class AssinarPixIn(BaseModel):
    plano:           str
    asaasCustomerId: str

class AssinarPixOut(BaseModel):
    subscriptionId: str
    plano:          str
    status:         str
    nextDueDate:    str
    value:          float
    pixQrCode:      str   # base64 PNG do QR Code
    pixKey:         str   # payload copia-e-cola
    pixExpiresAt:   str   # ISO datetime de expiração

@app.post("/k1/lex/auth/assinar-pix", response_model=AssinarPixOut)
def assinar_pix(body: AssinarPixIn, db: Session = Depends(get_db), payload=Depends(verify_token)):
    plano_cfg = PLANOS.get(body.plano)
    if not plano_cfg:
        raise HTTPException(400, f"Plano invalido: {body.plano}")

    tenant_id = payload.get("tenant_id")
    tenant = db.query(Tenant).filter_by(id=tenant_id).first()
    if not tenant:
        raise HTTPException(404, "Tenant nao encontrado")
    if tenant.asaas_customer_id != body.asaasCustomerId:
        raise HTTPException(403, "Cliente Asaas nao vinculado a esta conta")
    if tenant.asaas_subscription_id and tenant.subscription_status in ("pending", "active", "past_due"):
        raise HTTPException(409, "Ja existe uma assinatura vinculada a esta conta")

    now = datetime.utcnow()
    if tenant.plano == "trial" and tenant.trial_expires_at and tenant.trial_expires_at > now:
        next_due = tenant.trial_expires_at.strftime("%Y-%m-%d")
    else:
        next_due = (now + timedelta(days=1)).strftime("%Y-%m-%d")

    headers = {"access_token": KEALEX_ASAAS_API_KEY, "Content-Type": "application/json", "User-Agent": "Kealex/1.0.0"}

    # 1. Criar assinatura PIX
    try:
        resp = httpx.post(
            f"{ASAAS_BASE}/subscriptions",
            json={
                "customer":    body.asaasCustomerId,
                "billingType": "PIX",
                "nextDueDate": next_due,
                "value":       plano_cfg["value"],
                "cycle":       "MONTHLY",
                "description": plano_cfg["description"],
            },
            headers=headers,
            timeout=20,
        )
        if resp.status_code not in (200, 201):
            raise HTTPException(422, f"Asaas recusou: {resp.json().get('errors', resp.text)}")
        sub = resp.json()
        subscription_id = sub["id"]
    except httpx.TimeoutException:
        raise HTTPException(504, "Timeout ao conectar com Asaas")

    # 2. Buscar o pagamento gerado para a assinatura
    try:
        resp = httpx.get(
            f"{ASAAS_BASE}/payments",
            params={"subscription": subscription_id, "limit": 1},
            headers=headers,
            timeout=15,
        )
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

    # Persiste assinatura como pending
    tenant.asaas_subscription_id = subscription_id
    tenant.subscription_plan = body.plano
    tenant.subscription_status = "pending"
    tenant.next_due_date = due_date
    tenant.updated_at = datetime.utcnow()
    db.commit()

    expires_at = (now + timedelta(hours=24)).isoformat()

    return AssinarPixOut(
        subscriptionId=subscription_id,
        plano=body.plano,
        status="PENDING",
        nextDueDate=due_date,
        value=plano_cfg["value"],
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
        "postalCode": body.postalCode,
        "addressNumber": body.addressNumber,
        "complement": body.addressComplement,
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
        tenant.billing_cpf_cnpj = _digits(body.cpfCnpj)
        tenant.billing_phone = _digits(body.phone)
        tenant.billing_mobile_phone = _digits(body.mobilePhone)
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
        "cpfCnpj": cpf_cnpj or "",
        "phone": phone or "",
        "mobilePhone": mobile_phone or "",
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
        elif event_name == "SUBSCRIPTION_DELETED":
            tenant.subscription_status = "canceled"
        tenant.updated_at = datetime.utcnow()
    db.commit()
    return {"ok": True, "ignored": tenant is None}

@app.get("/k1/lex/auth/billing-status")
def billing_status(db: Session = Depends(get_db), payload=Depends(verify_token)):
    tenant = db.query(Tenant).filter_by(id=payload.get("tenant_id")).first()
    if not tenant:
        raise HTTPException(404, "Tenant nao encontrado")
    now = datetime.utcnow()
    if not tenant.ativo:
        status = "inactive"
    elif tenant.plano == "trial":
        status = "trial_expired" if tenant.trial_expires_at and tenant.trial_expires_at <= now else "trial"
    elif tenant.plano in ("starter", "professional", "enterprise"):
        status = tenant.subscription_status or "inactive"
    else:
        status = "inactive"
    return {
        "plano": tenant.plano,
        "status": status,
        "subscriptionStatus": tenant.subscription_status,
        "nextDueDate": tenant.next_due_date,
        "trialExpiresAt": tenant.trial_expires_at.isoformat() if tenant.trial_expires_at else None,
    }
@app.get("/health")
def health_simple():
    return {"status": "healthy", "service": "svc-auth"}

@app.get("/k1/lex/health")
def health():
    return {"status": "ok", "service": "svc-auth"}
