import uuid
from datetime import datetime

from sqlalchemy import Column, DateTime, Enum as SAEnum, Integer, String, Text
from sqlalchemy.orm import DeclarativeBase

from app.domain.entities.repository_types import StatusEnum, TipoRepositorioEnum


class Base(DeclarativeBase):
    pass


class Repositorio(Base):
    __tablename__ = "repositorios"

    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    tenant_id = Column(String(36), nullable=False)
    user_id = Column(String(36), nullable=False)
    nome = Column(String(255), nullable=False)
    tipo = Column(SAEnum(TipoRepositorioEnum, name="tipo_repo_enum"), nullable=False)
    status = Column(SAEnum(StatusEnum, name="status_repo_enum"), default=StatusEnum.ativo)
    url = Column(String(1000), nullable=True)
    caminho_local = Column(String(1000), nullable=True)
    gdrive_folder_id = Column(String(255), nullable=True)
    descricao = Column(Text, nullable=True)
    metadados = Column(Text, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)


class Arquivo(Base):
    __tablename__ = "arquivos"

    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    tenant_id = Column(String(36), nullable=False)
    repositorio_id = Column(String(36), nullable=False)
    nome = Column(String(255), nullable=False)
    caminho = Column(String(1000), nullable=False)
    tipo_mime = Column(String(100), nullable=True)
    tamanho_bytes = Column(Integer, default=0)
    hash_arquivo = Column(String(64), nullable=True)
    metadados = Column(Text, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
