from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from datetime import datetime, timedelta
import uuid
from jose import jwt
from app.core.config import KEALEX_SECRET_KEY, ALGORITHM, TRIAL_DAYS
from app.infrastructure.database.models.auth_models import Usuario, Tenant, Escritorio, RoleEnum
from app.infrastructure.database.session import get_db
from app.infrastructure.security.bcrypt_hasher import hash_password, verify_password
from app.infrastructure.security.jwt_provider import create_access_token, verify_token
from app.api.dependencies import require_active_trial
from app.api.schemas.auth_schema import LoginIn, RegisterIn, PreRegisterIn, PreRegisterOut
from app.api.schemas.user_schema import AuthUser
from app.core.normalization import digits

router = APIRouter()

@router.post("/k1/lex/auth/register", response_model=AuthUser, status_code=201)
def register(body: RegisterIn, db: Session = Depends(get_db)):
    cpf_cnpj = digits(body.cpfCnpj)
    if not cpf_cnpj or len(cpf_cnpj) not in (11, 14):
        raise HTTPException(400, "Informe um CPF ou CNPJ válido.")

    # e-mail já cadastrado?
    if db.query(Usuario).filter_by(email=body.email).first():
        raise HTTPException(409, "E-mail já cadastrado. Acesse /entrar para fazer login.")

    role_by_profile = {
        "advogado": RoleEnum.advogado,
        "escritorio": RoleEnum.escritorio,
        "juridico": RoleEnum.juridico,
        "corporativo": RoleEnum.juridico,
    }
    selected_role = role_by_profile.get(body.perfil)
    if selected_role is None:
        raise HTTPException(400, "Selecione um perfil válido para o cadastro.")
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
        billing_mobile_phone=digits(body.whatsapp),
    )
    db.add(tenant)
    db.flush()  # gera tenant.id sem commit

    office = None
    if selected_role == RoleEnum.escritorio:
        office = Escritorio(
            tenant_id=tenant.id,
            nome=body.nome,
            cnpj=cpf_cnpj if len(cpf_cnpj) == 14 else None,
            telefone=digits(body.whatsapp),
            email=body.email,
            limite_advogados=3,
            codigo="KX-" + uuid.uuid4().hex[:12].upper(),
        )
        db.add(office)
        db.flush()
    senha_final = body.senha if body.senha and len(body.senha) >= 6 else str(uuid.uuid4())[:8]
    user = Usuario(
        tenant_id=tenant.id,
        nome=body.nome,
        email=body.email,
        senha_hash=hash_password(senha_final),
        role=selected_role,
        escritorio_id=office.id if office else None,
        codigo=office.codigo if office else None,
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
        accessToken=create_access_token(user),
        plano=tenant.plano,
        subscriptionStatus=tenant.subscription_status,
        tenantAtivo=tenant.ativo,
        trialStartedAt=tenant.trial_started_at.isoformat(),
        trialExpiresAt=tenant.trial_expires_at.isoformat(),
        subscriptionExpiresAt=tenant.subscription_expires_at.isoformat() + "Z" if tenant.subscription_expires_at else None,
        escritorioId=getattr(user, 'escritorio_id', None),
        codigoEscritorio=getattr(user, 'codigo', None),
        escritorioNome=office.nome if office else None,
        modalidade="escritorio" if user.escritorio_id else "autonomo",
    )


@router.post("/k1/lex/auth/login", response_model=AuthUser)
def login(body: LoginIn, db: Session = Depends(get_db)):
    user = db.query(Usuario).filter_by(email=body.email, ativo=True).first()
    if not user or not verify_password(body.senha, user.senha_hash):
        raise HTTPException(401, "Credenciais inválidas")

    tenant = db.query(Tenant).filter_by(id=user.tenant_id).first()

    # Contas com trial vencido ainda podem autenticar para acessar a area de cobranca.

    return AuthUser(
        id=user.id,
        nome=user.nome,
        email=user.email,
        role=user.role,
        tenantId=user.tenant_id,
        accessToken=create_access_token(user),
        plano=tenant.plano if tenant else "trial",
        subscriptionStatus=tenant.subscription_status if tenant else None,
        tenantAtivo=tenant.ativo if tenant else False,
        trialStartedAt=tenant.trial_started_at.isoformat() if tenant and tenant.trial_started_at else None,
        trialExpiresAt=tenant.trial_expires_at.isoformat() if tenant and tenant.trial_expires_at else None,
        subscriptionExpiresAt=tenant.subscription_expires_at.isoformat() + "Z" if tenant and tenant.subscription_expires_at else None,
        escritorioId=getattr(user, 'escritorio_id', None),
        codigoEscritorio=getattr(user, 'codigo', None),
        escritorioNome=(db.query(Escritorio.nome).filter_by(id=user.escritorio_id, tenant_id=user.tenant_id).scalar() if user.escritorio_id else None),
        modalidade="escritorio" if user.escritorio_id else "autonomo",
    )

# ── Pre-registro (fluxo de assinatura) ───────────────────────────────────────

@router.post("/k1/lex/auth/pre-register", response_model=PreRegisterOut, status_code=201)
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
        senha_hash=hash_password(body.senha), role=RoleEnum.advogado,
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


@router.post("/k1/lex/auth/ativar", response_model=AuthUser)
def ativar_usuario(db: Session = Depends(get_db), payload=Depends(verify_token)):
    """Endpoint legado desativado: somente webhook autenticado altera entitlement."""
    raise HTTPException(410, "Ativacao manual desativada. Aguarde a confirmacao do pagamento.")


# ── Assinatura (Asaas) ────────────────────────────────────────────────────────

