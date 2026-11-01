import uuid
from datetime import datetime
from sqlalchemy import Column, DateTime, Index, Integer, String, Text
from sqlalchemy.dialects.mysql import LONGTEXT
from app.infrastructure.database.models.document_model import Base
LONG_TEXT = Text().with_variant(LONGTEXT(), "mysql")

class AnaliseConversa(Base):
    __tablename__ = "analise_documentos_conversas"
    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    tenant_id = Column(String(36), nullable=False, index=True)
    user_id = Column(String(36), nullable=False, index=True)
    titulo = Column(String(255), nullable=False, default="Nova análise documental")
    created_at = Column(DateTime, nullable=False, default=datetime.utcnow)
    updated_at = Column(DateTime, nullable=False, default=datetime.utcnow, onupdate=datetime.utcnow)


class AnaliseDocumento(Base):
    __tablename__ = "analise_documentos_arquivos"
    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    tenant_id = Column(String(36), nullable=False, index=True)
    user_id = Column(String(36), nullable=False, index=True)
    conversa_id = Column(String(36), nullable=False, index=True)
    nome = Column(String(255), nullable=False)
    extensao = Column(String(10), nullable=False)
    tamanho_bytes = Column(Integer, nullable=False)
    paginas = Column(Integer, nullable=True)
    chunks_json = Column(LONG_TEXT, nullable=False)
    created_at = Column(DateTime, nullable=False, default=datetime.utcnow)


class AnaliseMensagem(Base):
    __tablename__ = "analise_documentos_mensagens"
    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    tenant_id = Column(String(36), nullable=False, index=True)
    user_id = Column(String(36), nullable=False, index=True)
    conversa_id = Column(String(36), nullable=False, index=True)
    role = Column(String(20), nullable=False)
    content = Column(LONG_TEXT, nullable=False)
    created_at = Column(DateTime, nullable=False, default=datetime.utcnow)


Index("ix_analise_conversa_owner", AnaliseConversa.tenant_id, AnaliseConversa.user_id, AnaliseConversa.updated_at)
Index("ix_analise_documento_owner", AnaliseDocumento.tenant_id, AnaliseDocumento.user_id, AnaliseDocumento.conversa_id)
Index("ix_analise_mensagem_owner", AnaliseMensagem.tenant_id, AnaliseMensagem.user_id, AnaliseMensagem.conversa_id, AnaliseMensagem.created_at)
