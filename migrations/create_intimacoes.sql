CREATE TABLE IF NOT EXISTS intimacoes (
    id VARCHAR(36) NOT NULL,
    tenant_id VARCHAR(36) NOT NULL,
    user_id VARCHAR(36) NOT NULL,
    processo_id VARCHAR(36) NULL,
    processo_numero VARCHAR(50) NULL,
    processo_titulo VARCHAR(255) NULL,
    diario VARCHAR(255) NOT NULL,
    data_publicacao VARCHAR(40) NOT NULL,
    conteudo TEXT NOT NULL,
    resumo_ia TEXT NULL,
    prazo_calculado VARCHAR(40) NULL,
    status VARCHAR(20) NOT NULL DEFAULT 'nova',
    created_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    PRIMARY KEY (id),
    INDEX ix_intimacoes_tenant_id (tenant_id),
    INDEX ix_intimacoes_tenant_publicacao (tenant_id, data_publicacao)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;
