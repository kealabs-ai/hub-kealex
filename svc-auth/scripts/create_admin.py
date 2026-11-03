"""Interactively create an administrator for an existing tenant."""
import getpass

from app.infrastructure.database.models.auth_models import RoleEnum, Tenant, Usuario
from app.infrastructure.database.session import SessionLocal
from app.infrastructure.security.bcrypt_hasher import hash_password


tenant_slug = input("Slug do tenant existente: ").strip().lower()
name = input("Nome do administrador: ").strip()
email = input("E-mail do administrador: ").strip().lower()
password = getpass.getpass("Senha (mínimo 12 caracteres): ")
confirmation = getpass.getpass("Confirme a senha: ")
if not tenant_slug or not name or not email or len(password) < 12 or password != confirmation:
    raise SystemExit("Dados inválidos; informe tenant, nome, e-mail e uma senha forte confirmada.")

with SessionLocal() as db:
    tenant = db.query(Tenant).filter_by(slug=tenant_slug).first()
    if tenant is None:
        raise SystemExit("Tenant não encontrado.")
    if db.query(Usuario).filter_by(email=email).first():
        raise SystemExit("Já existe um usuário com esse e-mail.")
    db.add(
        Usuario(
            tenant_id=tenant.id,
            nome=name,
            email=email,
            senha_hash=hash_password(password),
            role=RoleEnum.admin,
            ativo=True,
        )
    )
    db.commit()

print("Administrador criado para o tenant informado.")
