-- ============================================================
-- Migration: criar tabela clientes
-- Associada ao advogado responsável (advogado_id → usuarios.id)
-- ============================================================

CREATE TABLE IF NOT EXISTS clientes (
    id            VARCHAR(36)   NOT NULL PRIMARY KEY,
    tenant_id     VARCHAR(36)   NOT NULL,
    advogado_id   VARCHAR(36)   NOT NULL,          -- FK → usuarios.id (role = advogado)
    nome          VARCHAR(255)  NOT NULL,
    email         VARCHAR(255)  NOT NULL,
    telefone      VARCHAR(50)   NULL,
    cpf_cnpj      VARCHAR(20)   NULL,
    endereco      VARCHAR(500)  NULL,
    observacoes   TEXT          NULL,
    created_at    DATETIME      NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at    DATETIME      NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,

    INDEX idx_clientes_tenant   (tenant_id),
    INDEX idx_clientes_advogado (advogado_id),
    UNIQUE KEY uq_cliente_email_tenant (email, tenant_id)
);

-- ============================================================
-- Ajuste em processos: cliente_id agora referencia clientes.id
-- (a coluna já existe; apenas documenta a nova semântica)
-- Se precisar recriar a FK explicitamente:
-- ALTER TABLE processos
--     ADD CONSTRAINT fk_processo_cliente
--     FOREIGN KEY (cliente_id) REFERENCES clientes(id);
-- ============================================================
