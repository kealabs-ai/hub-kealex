import uuid
from datetime import datetime
from sqlalchemy import Column, DateTime, String, Text
from sqlalchemy.orm import DeclarativeBase

class Base(DeclarativeBase): pass

class Cliente(Base):
    __tablename__ = "clientes"
    id            = Column(String(36),  primary_key=True, default=lambda: str(uuid.uuid4()))
    tenant_id     = Column(String(36),  nullable=False)
    advogado_id   = Column(String(36),  nullable=False)   # usuario com role=advogado responsável
    nome          = Column(String(255), nullable=False)
    email         = Column(String(255), nullable=False)
    telefone      = Column(String(50),  nullable=True)
    cpf_cnpj      = Column(String(20),  nullable=True)
    endereco      = Column(String(500), nullable=True)
    observacoes   = Column(Text,        nullable=True)
    created_at    = Column(DateTime,    default=datetime.utcnow)
    updated_at    = Column(DateTime,    default=datetime.utcnow, onupdate=datetime.utcnow)
