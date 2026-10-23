-- Chaves públicas cadastradas por usuário e órgão para uso nas integrações.
CREATE TABLE usuarios_chaves_publicas (
    id VARCHAR(36) NOT NULL,
    user_id VARCHAR(36) NOT NULL,
    orgao VARCHAR(120) NOT NULL,
    chave_publica TEXT NOT NULL,
    created_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    PRIMARY KEY (id),
    CONSTRAINT fk_usuario_chaves_publicas_usuario
        FOREIGN KEY (user_id) REFERENCES usuarios (id) ON DELETE CASCADE,
    CONSTRAINT uq_usuario_chave_publica_orgao UNIQUE (user_id, orgao),
    INDEX ix_usuarios_chaves_publicas_user_id (user_id)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;
