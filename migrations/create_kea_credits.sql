CREATE TABLE IF NOT EXISTS carteiras_keacreditos (
    id VARCHAR(36) NOT NULL PRIMARY KEY,
    organizacao_id VARCHAR(36) NOT NULL,
    saldo_creditos INT NOT NULL DEFAULT 0,
    criado_em DATETIME NOT NULL,
    atualizado_em DATETIME NOT NULL,
    CONSTRAINT uq_carteiras_keacreditos_organizacao UNIQUE (organizacao_id),
    CONSTRAINT fk_carteiras_keacreditos_organizacao FOREIGN KEY (organizacao_id) REFERENCES tenants(id) ON DELETE CASCADE
);

CREATE TABLE IF NOT EXISTS transacoes_keacreditos (
    id VARCHAR(36) NOT NULL PRIMARY KEY,
    organizacao_id VARCHAR(36) NOT NULL,
    usuario_id VARCHAR(36) NOT NULL,
    tipo VARCHAR(20) NOT NULL,
    status VARCHAR(20) NOT NULL,
    quantidade_creditos INT NOT NULL,
    valor_centavos INT NULL,
    saldo_antes INT NULL,
    saldo_depois INT NULL,
    chave_idempotencia VARCHAR(120) NOT NULL,
    pacote_id VARCHAR(40) NULL,
    descricao VARCHAR(240) NOT NULL,
    asaas_pagamento_id VARCHAR(80) NULL,
    codigo_qr_pix TEXT NULL,
    codigo_copia_cola_pix TEXT NULL,
    pix_expira_em DATETIME NULL,
    criado_em DATETIME NOT NULL,
    confirmado_em DATETIME NULL,
    CONSTRAINT uq_transacoes_keacreditos_idempotencia UNIQUE (organizacao_id, chave_idempotencia),
    CONSTRAINT uq_transacoes_keacreditos_asaas_pagamento UNIQUE (asaas_pagamento_id),
    CONSTRAINT fk_transacoes_keacreditos_organizacao FOREIGN KEY (organizacao_id) REFERENCES tenants(id) ON DELETE CASCADE,
    CONSTRAINT fk_transacoes_keacreditos_usuario FOREIGN KEY (usuario_id) REFERENCES usuarios(id) ON DELETE CASCADE,
    INDEX ix_transacoes_keacreditos_escopo_criado (organizacao_id, criado_em),
    INDEX ix_transacoes_keacreditos_status (organizacao_id, status)
);
