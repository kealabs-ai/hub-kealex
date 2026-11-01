import uuid
from datetime import datetime
from sqlalchemy import Column, DateTime, Integer, String, Enum as SAEnum
from sqlalchemy.orm import DeclarativeBase
from app.domain.entities.honorario_status import StatusEnum

class Base(DeclarativeBase): pass

class Honorario(Base):
    __tablename__ = "honorarios"
    id              = Column(String(36),  primary_key=True, default=lambda: str(uuid.uuid4()))
    tenant_id       = Column(String(36),  nullable=False)
    user_id         = Column(String(36),  nullable=False)
    escritorio_id   = Column(String(36),  nullable=True)
    processo_id     = Column(String(36),  nullable=False)
    cliente_id      = Column(String(36),  nullable=False)
    advogado_id     = Column(String(36),  nullable=False)
    descricao       = Column(String(500), default="")
    valor_centavos  = Column(Integer,     nullable=False)
    data_vencimento = Column(String(10),  nullable=False)
    data_pagamento  = Column(String(10),  nullable=True)
    status          = Column(SAEnum(StatusEnum, name="status_honorario_enum"), default=StatusEnum.pendente)
    created_at      = Column(DateTime,    default=datetime.utcnow)
    updated_at      = Column(DateTime,    default=datetime.utcnow, onupdate=datetime.utcnow)

