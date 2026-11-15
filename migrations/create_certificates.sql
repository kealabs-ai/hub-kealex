CREATE TABLE IF NOT EXISTS solicitacoes_certidoes (
    id VARCHAR(36) PRIMARY KEY,
    organizacao_id VARCHAR(36) NOT NULL,
    usuario_id VARCHAR(36) NOT NULL,
    emissor VARCHAR(40) NOT NULL,
    tipo_certidao VARCHAR(120) NOT NULL,
    tipo_titular VARCHAR(20) NOT NULL,
    identificador_mascarado VARCHAR(32) NOT NULL,
    hash_identificador VARCHAR(64) NOT NULL,
    dados_solicitacao TEXT NOT NULL,
    protocolo_externo VARCHAR(120) NULL,
    status VARCHAR(40) NOT NULL,
    codigo_erro VARCHAR(80) NULL,
    url_portal VARCHAR(500) NULL,
    criado_em DATETIME NOT NULL,
    atualizado_em DATETIME NOT NULL,
    concluido_em DATETIME NULL,
    INDEX ix_solicitacoes_certidoes_organizacao_id (organizacao_id),
    INDEX ix_solicitacoes_certidoes_usuario_id (usuario_id),
    INDEX ix_solicitacoes_certidoes_escopo_criado_em (organizacao_id, usuario_id, criado_em)
);

CREATE TABLE IF NOT EXISTS certidoes (
    id VARCHAR(36) PRIMARY KEY,
    solicitacao_id VARCHAR(36) NOT NULL UNIQUE,
    numero_certidao VARCHAR(120) NULL,
    emitida_em DATETIME NULL,
    validade_em DATETIME NULL,
    codigo_verificacao VARCHAR(120) NULL,
    fonte_oficial VARCHAR(500) NULL,
    origem_upload VARCHAR(30) NOT NULL,
    status_validacao VARCHAR(30) NOT NULL,
    hash_arquivo VARCHAR(64) NOT NULL,
    tipo_conteudo VARCHAR(80) NOT NULL,
    nome_arquivo VARCHAR(180) NOT NULL,
    arquivo LONGBLOB NOT NULL,
    criado_em DATETIME NOT NULL,
    CONSTRAINT fk_certidoes_solicitacao FOREIGN KEY (solicitacao_id) REFERENCES solicitacoes_certidoes(id) ON DELETE CASCADE,
    INDEX ix_certidoes_solicitacao_id (solicitacao_id)
);

CREATE TABLE IF NOT EXISTS auditoria_certidoes (
    id VARCHAR(36) PRIMARY KEY,
    solicitacao_id VARCHAR(36) NOT NULL,
    organizacao_id VARCHAR(36) NOT NULL,
    usuario_id VARCHAR(36) NOT NULL,
    acao VARCHAR(40) NOT NULL,
    status VARCHAR(40) NOT NULL,
    criado_em DATETIME NOT NULL,
    CONSTRAINT fk_auditoria_certidoes_solicitacao FOREIGN KEY (solicitacao_id) REFERENCES solicitacoes_certidoes(id) ON DELETE CASCADE,
    INDEX ix_auditoria_certidoes_solicitacao_id (solicitacao_id),
    INDEX ix_auditoria_certidoes_organizacao_id (organizacao_id)
);
