import os, uuid, enum
from datetime import datetime, timedelta
from fastapi import FastAPI, HTTPException, Depends
from fastapi.middleware.cors import CORSMiddleware
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from pydantic import BaseModel, EmailStr
import bcrypt
from jose import jwt, JWTError
from sqlalchemy import create_engine, Column, String, Boolean, DateTime, Enum as SAEnum
from sqlalchemy.orm import DeclarativeBase, Session, sessionmaker

# ── Config ────────────────────────────────────────────────────────────────────

def _get_database_url(default: str) -> str:
    raw = os.getenv("DATABASE_URL")
    if raw is None or raw.strip().lower() in ("", "null", "none"):
        return default
    return raw.strip()

DATABASE_URL         = _get_database_url(
    "mysql+pymysql://u549746795_kealex:Sally2026%40%21%40@srv1078.hstgr.io:3306/u549746795_kealex"
)
SECRET_KEY           = os.getenv("SECRET_KEY", "changeme-secret-key")
ALGORITHM            = "HS256"
TOKEN_EXPIRE_MINUTES = 60 * 8
TRIAL_DAYS           = 7

engine       = create_engine(DATABASE_URL, pool_pre_ping=True, pool_recycle=280, pool_size=5, max_overflow=10)
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
        SECRET_KEY, ALGORITHM,
    )

def verify_token(creds: HTTPAuthorizationCredentials = Depends(bearer)):
    try:
        return jwt.decode(creds.credentials, SECRET_KEY, algorithms=[ALGORITHM])
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

    # Admin nunca é bloqueado, mas demais roles são verificados
    if user.role != RoleEnum.admin:
        _check_trial(tenant, user.role)

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

    tenant = Tenant(
        nome=body.nome, slug=slug,
        plano="pendente",  # pendente ate pagamento
        ativo=False,
    )
    db.add(tenant)
    db.flush()

    user = Usuario(
        tenant_id=tenant.id, nome=body.nome, email=body.email,
        senha_hash=_hash(body.senha), role=RoleEnum.advogado,
        ativo=False,  # inativo ate pagamento
    )
    db.add(user)
    db.commit()
    db.refresh(user)

    # token temporario para o fluxo de assinatura (nao passa pelo trial guard)
    token = jwt.encode(
        {"sub": user.id, "role": user.role, "tenant_id": tenant.id,
         "exp": datetime.utcnow() + timedelta(hours=2), "pre": True},
        SECRET_KEY, ALGORITHM,
    )
    print(f"[PRE-REGISTER] usuario inativo criado: {body.email} | tenant={tenant.id}")
    return PreRegisterOut(userId=user.id, tenantId=tenant.id, token=token)


@app.post("/k1/lex/auth/ativar", response_model=AuthUser)
def ativar_usuario(db: Session = Depends(get_db), payload=Depends(verify_token)):
    """Ativa usuario + tenant apos pagamento confirmado. Chamado internamente pelo /assinar."""
    user_id   = payload.get("sub")
    tenant_id = payload.get("tenant_id")

    user   = db.query(Usuario).filter_by(id=user_id).first()
    tenant = db.query(Tenant).filter_by(id=tenant_id).first()
    if not user or not tenant:
        raise HTTPException(404, "Usuario ou tenant nao encontrado")

    now = datetime.utcnow()
    user.ativo   = True
    tenant.ativo = True
    # nao inicia trial — plano ja sera definido pelo /assinar
    tenant.updated_at = now
    user.updated_at   = now
    db.commit()
    db.refresh(user)
    db.refresh(tenant)

    return AuthUser(
        id=user.id, nome=user.nome, email=user.email, role=user.role,
        tenantId=tenant.id, accessToken=_make_token(user),
        plano=tenant.plano,
        trialStartedAt=tenant.trial_started_at.isoformat() if tenant.trial_started_at else None,
        trialExpiresAt=tenant.trial_expires_at.isoformat() if tenant.trial_expires_at else None,
        escritorioId=user.escritorio_id,
        modalidade="escritorio" if user.escritorio_id else "autonomo",
    )


# ── Assinatura (Asaas) ────────────────────────────────────────────────────────

import httpx

ASAAS_API_KEY = os.getenv("ASAAS_API_KEY", "")
ASAAS_BASE    = os.getenv("ASAAS_BASE_URL", "https://api-sandbox.asaas.com/v3")

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
            "cpfCnpj":            body.holderInfo.cpfCnpj,
            "postalCode":         body.holderInfo.postalCode,
            "addressNumber":      body.holderInfo.addressNumber,
            "addressComplement":  body.holderInfo.addressComplement,
            "phone":              body.holderInfo.phone,
            "mobilePhone":        body.holderInfo.mobilePhone,
        },
        "remoteIp": body.remoteIp,
    }

    try:
        resp = httpx.post(
            f"{ASAAS_BASE}/subscriptions",
            json=payload_asaas,
            headers={"access_token": ASAAS_API_KEY, "Content-Type": "application/json"},
            timeout=20,
        )
        if resp.status_code not in (200, 201):
            detail = resp.json().get("errors", resp.text)
            raise HTTPException(422, f"Asaas recusou: {detail}")
        data = resp.json()
    except httpx.TimeoutException:
        raise HTTPException(504, "Timeout ao conectar com Asaas")

    # Atualiza plano do tenant e ativa usuario/tenant se ainda inativo
    tenant.plano = body.plano
    tenant.updated_at = datetime.utcnow()
    if not tenant.ativo:
        tenant.ativo = True
    user = db.query(Usuario).filter_by(tenant_id=tenant_id, role=RoleEnum.advogado).first()
    if user and not user.ativo:
        user.ativo = True
        user.updated_at = datetime.utcnow()
    db.commit()

    return AssinarOut(
        subscriptionId=data.get("id", ""),
        plano=body.plano,
        status=data.get("status", "ACTIVE"),
        nextDueDate=data.get("nextDueDate", next_due),
        value=plano_cfg["value"],
    )


@app.post("/k1/lex/auth/criar-cliente-asaas")
def criar_cliente_asaas(body: HolderInfoIn, payload=Depends(verify_token)):
    """Cria ou recupera um customer no Asaas para o usuario autenticado."""
    try:
        resp = httpx.post(
            f"{ASAAS_BASE}/customers",
            json={
                "name":     body.name,
                "email":    body.email,
                "cpfCnpj": body.cpfCnpj,
                "phone":    body.phone,
                "mobilePhone": body.mobilePhone,
            },
            headers={"access_token": ASAAS_API_KEY, "Content-Type": "application/json"},
            timeout=15,
        )
        if resp.status_code not in (200, 201):
            detail = resp.json().get("errors", resp.text)
            raise HTTPException(422, f"Asaas recusou: {detail}")
        return {"customerId": resp.json().get("id")}
    except httpx.TimeoutException:
        raise HTTPException(504, "Timeout ao conectar com Asaas")

@app.get("/health")
def health_simple():
    return {"status": "healthy", "service": "svc-auth"}

@app.get("/k1/lex/health")
def health():
    return {"status": "ok", "service": "svc-auth"}
