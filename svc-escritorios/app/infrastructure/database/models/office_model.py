import uuid
from datetime import datetime
from sqlalchemy import Boolean, Column, DateTime, Integer, String
from sqlalchemy.orm import DeclarativeBase

class Base(DeclarativeBase): pass

class Escritorio(Base):
    __tablename__ = "escritorios"
    id         = Column(String(36),  primary_key=True, default=lambda: str(uuid.uuid4()))
    tenant_id  = Column(String(36),  nullable=False)
    nome       = Column(String(255), nullable=False)
    cnpj       = Column(String(18),  nullable=True)
    endereco   = Column(String(500), nullable=True)
    telefone   = Column(String(20),  nullable=True)
    email      = Column(String(255), nullable=True)
    limite_advogados = Column(Integer, nullable=False, default=3, server_default="3")
    codigo = Column(String(16), nullable=False, unique=True)
    ativo      = Column(Boolean,     default=True)
    created_at = Column(DateTime,    default=datetime.utcnow)
    updated_at = Column(DateTime,    default=datetime.utcnow, onupdate=datetime.utcnow)

