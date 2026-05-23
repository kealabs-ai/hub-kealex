import os
import bcrypt
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

new_hash = bcrypt.hashpw(b"admin123", bcrypt.gensalt()).decode()

with engine.connect() as conn:
    result = conn.execute(text("SELECT id, email, senha_hash FROM usuarios WHERE email = 'admin@kealex.com'"))
    row = result.fetchone()
    if row:
        print(f"Encontrado: {row.email}")
        print(f"Hash atual: {repr(row.senha_hash)}")
        conn.execute(text("UPDATE usuarios SET senha_hash = :h WHERE email = 'admin@kealex.com'"), {"h": new_hash})
        conn.commit()
        print(f"Hash novo:  {new_hash[:30]}...")
    else:
        conn.execute(text(
            "INSERT INTO usuarios (id, nome, email, senha_hash, role, ativo) VALUES (UUID(), 'Admin Kealex', 'admin@kealex.com', :h, 'admin', 1)"
        ), {"h": new_hash})
        conn.commit()
        print("Admin criado com hash correto")
