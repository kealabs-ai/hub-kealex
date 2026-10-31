import uuid
from datetime import datetime
from sqlalchemy import Boolean, Column, DateTime, ForeignKey, String, Text as SAText, UniqueConstraint
from sqlalchemy.orm import DeclarativeBase
from app.domain.entities.role import RoleEnum

class Base(DeclarativeBase): pass

class Usuario(Base):
    __tablename__ = "usuarios"
    id           = Column(String(36),  primary_key=True, default=lambda: str(uuid.uuid4()))
    tenant_id    = Column(String(36),  nullable=False)
    escritorio_id = Column(String(36), nullable=True)
    codigo = Column(String(16), nullable=True)
    oab = Column(String(50), nullable=True)
    nome         = Column(String(255), nullable=False)
    email        = Column(String(255), nullable=False)
    senha_hash   = Column(String(255), nullable=False)
    role         = Column(SAEnum(RoleEnum, name="role_enum_auth"), nullable=False)
    ativo        = Column(Boolean,     default=True)
    created_at   = Column(DateTime,    default=datetime.utcnow)
    updated_at   = Column(DateTime,    default=datetime.utcnow, onupdate=datetime.utcnow)

class UsuarioChavePublica(Base):
    __tablename__ = "usuarios_chaves_publicas"
    __table_args__ = (UniqueConstraint("user_id", "orgao", name="uq_usuario_chave_publica_orgao"),)
    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    user_id = Column(String(36), ForeignKey("usuarios.id", ondelete="CASCADE"), nullable=False, index=True)
    orgao = Column(String(120), nullable=False)
    chave_publica = Column(SAText, nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)
