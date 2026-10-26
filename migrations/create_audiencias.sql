CREATE TABLE IF NOT EXISTS audiencias (
    id VARCHAR(36) NOT NULL,
    tenant_id VARCHAR(36) NOT NULL,
    user_id VARCHAR(36) NOT NULL,
    processo_id VARCHAR(36) NULL,
    processo_titulo VARCHAR(255) NOT NULL DEFAULT '',
    tipo VARCHAR(80) NOT NULL DEFAULT '',
    data_hora VARCHAR(40) NOT NULL DEFAULT '',
    local VARCHAR(255) NOT NULL DEFAULT '',
    juiz VARCHAR(255) NULL,
    partes TEXT NULL,
    observacoes TEXT NULL,
    roteiro TEXT NULL,
    status VARCHAR(20) NOT NULL DEFAULT 'agendada',
    created_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    PRIMARY KEY (id),
    INDEX ix_audiencias_tenant_data_hora (tenant_id, data_hora)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;
