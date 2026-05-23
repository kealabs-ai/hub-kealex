import os, bcrypt
from sqlalchemy import create_engine, text

def _get_database_url() -> str:
    raw = os.getenv("DATABASE_URL")
    if raw is None or raw.strip().lower() in ("", "null", "none"):
        raise RuntimeError(
            "DATABASE_URL environment variable is missing or invalid. "
            "Set DATABASE_URL to a valid SQLAlchemy URL."
        )
    return raw.strip()

DATABASE_URL = _get_database_url()
engine = create_engine(DATABASE_URL, pool_pre_ping=True)

users = [
    ("Advogado Teste", "adv@kealex.com",     "adv123",  "advogado"),
    ("Cliente Teste",  "cliente@kealex.com", "cli123",  "cliente"),
]

with engine.connect() as conn:
    for nome, email, senha, role in users:
        exists = conn.execute(text("SELECT id FROM usuarios WHERE email = :e"), {"e": email}).fetchone()
        if exists:
            print(f"Já existe: {email}")
            continue
        h = bcrypt.hashpw(senha.encode(), bcrypt.gensalt()).decode()
        conn.execute(text(
            "INSERT INTO usuarios (id, nome, email, senha_hash, role, ativo) VALUES (UUID(), :n, :e, :h, :r, 1)"
        ), {"n": nome, "e": email, "h": h, "r": role})
        conn.commit()
        print(f"Criado: {email} ({role})")
