import uuid
from datetime import datetime
from sqlalchemy import Column, DateTime, String, Enum as SAEnum
from sqlalchemy.orm import DeclarativeBase
from app.domain.entities.prazo_status import StatusEnum

class Base(DeclarativeBase): pass

class Prazo(Base):
    __tablename__ = "prazos"
    id              = Column(String(36),   primary_key=True, default=lambda: str(uuid.uuid4()))
    tenant_id       = Column(String(36),   nullable=False)
    user_id         = Column(String(36),   nullable=False)
    escritorio_id   = Column(String(36),   nullable=True)
    processo_id     = Column(String(36),   nullable=False)
    advogado_id     = Column(String(36),   nullable=False)
    titulo          = Column(String(255),  nullable=False)
    descricao       = Column(String(1000), default="")
    data_vencimento = Column(String(10),   nullable=False)
    status          = Column(SAEnum(StatusEnum, name="status_prazo_enum"), default=StatusEnum.pendente)
    created_at      = Column(DateTime,     default=datetime.utcnow)
    updated_at      = Column(DateTime,     default=datetime.utcnow, onupdate=datetime.utcnow)

