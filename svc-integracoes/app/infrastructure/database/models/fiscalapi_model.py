import uuid
from datetime import datetime

from sqlalchemy import Boolean, Column, DateTime, Index, Integer, LargeBinary, String, Text, UniqueConstraint
from sqlalchemy.dialects.mysql import LONGTEXT, MEDIUMBLOB
from sqlalchemy.orm import DeclarativeBase


class Base(DeclarativeBase):
    pass


class FiscalApiConsulta(Base):
    __tablename__ = "consultas_fiscalapi"
    __table_args__ = (
        UniqueConstraint("organizacao_id", "usuario_id", "chave_idempotencia", name="uq_consultas_fiscalapi_idempotencia"),
        Index("ix_consultas_fiscalapi_escopo_data", "organizacao_id", "usuario_id", "criado_em"),
        Index("ix_consultas_fiscalapi_servico_status", "organizacao_id", "servico", "status"),
    )

    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    tenant_id = Column("organizacao_id", String(36), nullable=False)
    user_id = Column("usuario_id", String(36), nullable=False)
    service = Column("servico", String(50), nullable=False)
    provider = Column("fornecedor", String(40), nullable=False, default="fiscalapi")
    idempotency_key = Column("chave_idempotencia", String(120), nullable=False)
    request_hash = Column("hash_solicitacao", String(64), nullable=False)
    subject_type = Column("tipo_identificador", String(10), nullable=True)
    subject_masked = Column("identificador_mascarado", String(40), nullable=True)
    subject_hash = Column("hash_identificador", String(64), nullable=True)
    provider_request_id = Column("id_requisicao_fornecedor", String(100), nullable=True)
    status = Column(String(30), nullable=False, default="PROCESSANDO")
    document_available = Column("documento_disponivel", Boolean, nullable=False, default=False)
    normalized_result_json = Column("resultado_json", Text().with_variant(LONGTEXT(), "mysql"), nullable=True)
    provider_response_json = Column("resposta_original_json", Text().with_variant(LONGTEXT(), "mysql"), nullable=True)
    error_code = Column("codigo_erro", String(80), nullable=True)
    public_error = Column("erro_publico", String(240), nullable=True)
    http_error_code = Column("codigo_http_erro", Integer, nullable=True)
    retry_after = Column("repetir_apos", String(20), nullable=True)
    operational_cost_cents = Column("custo_operacional_centavos", Integer, nullable=True)
    created_at = Column("criado_em", DateTime, nullable=False, default=datetime.utcnow)
    completed_at = Column("concluido_em", DateTime, nullable=True)


class FiscalApiDocumento(Base):
    __tablename__ = "documentos_fiscalapi"

    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    consultation_id = Column("consulta_id", String(36), nullable=False, unique=True, index=True)
    file_hash = Column("hash_arquivo", String(64), nullable=False)
    filename = Column("nome_arquivo", String(180), nullable=False)
    file_data = Column("arquivo_criptografado", LargeBinary().with_variant(MEDIUMBLOB(), "mysql"), nullable=False)
    size_bytes = Column("tamanho_bytes", Integer, nullable=False)
    created_at = Column("criado_em", DateTime, nullable=False, default=datetime.utcnow)
