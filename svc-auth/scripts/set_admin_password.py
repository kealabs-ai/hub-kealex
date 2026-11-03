"""Interactively rotate the password for an existing admin account."""
import getpass
import os
import sys

import bcrypt
from sqlalchemy import create_engine, text


database_url = os.getenv("KEALEX_DATABASE_URL")
if not database_url:
    raise RuntimeError("Configure KEALEX_DATABASE_URL before running this utility")

email = input("Email da conta administrativa existente: ").strip().lower()
password = getpass.getpass("Nova senha: ")
confirmation = getpass.getpass("Confirme a nova senha: ")
if not email or len(password) < 12 or password != confirmation:
    raise SystemExit("Informe o e-mail, use pelo menos 12 caracteres e confirme a mesma senha.")

password_hash = bcrypt.hashpw(password.encode("utf-8"), bcrypt.gensalt()).decode("utf-8")
engine = create_engine(database_url, pool_pre_ping=True)
with engine.begin() as connection:
    result = connection.execute(
        text("UPDATE usuarios SET senha_hash = :password_hash WHERE email = :email AND role = 'admin'"),
        {"password_hash": password_hash, "email": email},
    )
    if result.rowcount != 1:
        raise SystemExit("Nenhuma conta administrativa foi atualizada; verifique o e-mail e o tenant.")

print("Senha da conta administrativa atualizada.")
