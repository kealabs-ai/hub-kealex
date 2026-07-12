-- ============================================================================
-- SCRIPT DE CRIAÇÃO - TABELAS DE COBRANÇA
-- ============================================================================
-- Descrição: Estrutura de banco de dados para o microserviço svc-cobrancas
-- Data: 2024
-- ============================================================================

-- ============================================================================
-- TABELA: cobrancas
-- Descrição: Armazena informações de cobrança
-- ============================================================================
CREATE TABLE IF NOT EXISTS cobrancas (
    id VARCHAR(36) PRIMARY KEY COMMENT 'UUID único da cobrança',
    tenant_id VARCHAR(36) NOT NULL COMMENT 'ID do tenant (multitenancy)',
    user_id VARCHAR(36) NOT NULL COMMENT 'ID do usuário que criou',
    processo_id VARCHAR(36) NOT NULL COMMENT 'ID do processo relacionado',
    cliente_id VARCHAR(36) NOT NULL COMMENT 'ID do cliente',
    valor_centavos INT NOT NULL COMMENT 'Valor em centavos (ex: 10000 = R$ 100,00)',
    status VARCHAR(50) NOT NULL DEFAULT 'pendente' COMMENT 'Status: pendente, pago, cancelado',
    fase_atual INT NOT NULL DEFAULT 0 COMMENT 'Fase atual (0-4)',
    data_vencimento DATETIME NULL COMMENT 'Data de vencimento da cobrança',
    data_pagamento DATETIME NULL COMMENT 'Data quando foi marcada como paga',
    motivo_cancelamento VARCHAR(500) NULL COMMENT 'Motivo do cancelamento se aplicável',
    created_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP COMMENT 'Data de criação',
    updated_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP COMMENT 'Data da última atualização',
    
    -- Índices para performance
    INDEX idx_tenant_id (tenant_id),
    INDEX idx_processo_id (processo_id),
    INDEX idx_cliente_id (cliente_id),
    INDEX idx_status (status),
    INDEX idx_fase_atual (fase_atual),
    INDEX idx_created_at (created_at),
    INDEX idx_tenant_status (tenant_id, status),
    INDEX idx_tenant_processo (tenant_id, processo_id)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci
COMMENT='Tabela de cobrancas com rastreamento de fases e status';

-- ============================================================================
-- TABELA: historico_cobrancas
-- Descrição: Armazena histórico de todas as ações em cobrancas
-- ============================================================================
CREATE TABLE IF NOT EXISTS historico_cobrancas (
    id VARCHAR(36) PRIMARY KEY COMMENT 'UUID único do histórico',
    cobranca_id VARCHAR(36) NOT NULL COMMENT 'ID da cobrança relacionada',
    acao VARCHAR(100) NOT NULL COMMENT 'Tipo de ação: criada, fase_avancada, marcado_pago, cancelada',
    fase_anterior INT NULL COMMENT 'Fase anterior (se aplicável)',
    fase_nova INT NULL COMMENT 'Fase nova (se aplicável)',
    status_anterior VARCHAR(50) NULL COMMENT 'Status anterior (se aplicável)',
    status_novo VARCHAR(50) NULL COMMENT 'Status novo (se aplicável)',
    observacao VARCHAR(500) NULL COMMENT 'Observações sobre a ação',
    created_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP COMMENT 'Data da ação',
    
    -- Índices para performance
    INDEX idx_cobranca_id (cobranca_id),
    INDEX idx_acao (acao),
    INDEX idx_created_at (created_at),
    INDEX idx_cobranca_created (cobranca_id, created_at),
    
    -- Constraint de integridade referencial
    CONSTRAINT fk_historico_cobranca FOREIGN KEY (cobranca_id) 
        REFERENCES cobrancas(id) ON DELETE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci
COMMENT='Histórico de todas as ações realizadas em cobrancas';

-- ============================================================================
-- VIEWS ÚTEIS
-- ============================================================================

-- View: Cobrancas por Status
CREATE OR REPLACE VIEW vw_cobrancas_por_status AS
SELECT 
    status,
    COUNT(*) as total,
    SUM(valor_centavos) as valor_total_centavos,
    SUM(valor_centavos) / 100 as valor_total_reais
FROM cobrancas
GROUP BY status;

-- View: Cobrancas Vencidas
CREATE OR REPLACE VIEW vw_cobrancas_vencidas AS
SELECT 
    id,
    tenant_id,
    processo_id,
    cliente_id,
    valor_centavos,
    status,
    fase_atual,
    data_vencimento,
    DATEDIFF(CURDATE(), DATE(data_vencimento)) as dias_vencido
FROM cobrancas
WHERE status = 'pendente' 
    AND data_vencimento IS NOT NULL 
    AND DATE(data_vencimento) < CURDATE()
ORDER BY data_vencimento ASC;

-- View: Cobrancas Próximas de Vencer
CREATE OR REPLACE VIEW vw_cobrancas_proximas_vencer AS
SELECT 
    id,
    tenant_id,
    processo_id,
    cliente_id,
    valor_centavos,
    status,
    fase_atual,
    data_vencimento,
    DATEDIFF(DATE(data_vencimento), CURDATE()) as dias_para_vencer
FROM cobrancas
WHERE status = 'pendente' 
    AND data_vencimento IS NOT NULL 
    AND DATE(data_vencimento) BETWEEN CURDATE() AND DATE_ADD(CURDATE(), INTERVAL 7 DAY)
ORDER BY data_vencimento ASC;

-- View: Resumo de Cobrancas por Tenant
CREATE OR REPLACE VIEW vw_resumo_cobrancas_tenant AS
SELECT 
    c.tenant_id,
    COUNT(DISTINCT c.id) as total_cobrancas,
    SUM(CASE WHEN c.status = 'pendente' THEN 1 ELSE 0 END) as pendentes,
    SUM(CASE WHEN c.status = 'pago' THEN 1 ELSE 0 END) as pagas,
    SUM(CASE WHEN c.status = 'cancelado' THEN 1 ELSE 0 END) as canceladas,
    SUM(CASE WHEN c.status = 'pendente' THEN c.valor_centavos ELSE 0 END) / 100 as valor_pendente_reais,
    SUM(CASE WHEN c.status = 'pago' THEN c.valor_centavos ELSE 0 END) / 100 as valor_pago_reais,
    SUM(c.valor_centavos) / 100 as valor_total_reais
FROM cobrancas c
GROUP BY c.tenant_id;

-- View: Timeline de Cobrança
CREATE OR REPLACE VIEW vw_timeline_cobranca AS
SELECT 
    hc.cobranca_id,
    hc.id as evento_id,
    hc.acao,
    hc.fase_anterior,
    hc.fase_nova,
    hc.status_anterior,
    hc.status_novo,
    hc.observacao,
    hc.created_at,
    c.status as status_atual,
    c.fase_atual,
    c.valor_centavos
FROM historico_cobrancas hc
JOIN cobrancas c ON hc.cobranca_id = c.id
ORDER BY hc.created_at ASC;

-- ============================================================================
-- PROCEDURES ÚTEIS
-- ============================================================================

-- Procedure: Obter Próximas Ações de uma Cobrança
DELIMITER //
CREATE PROCEDURE sp_proximas_acoes_cobranca(
    IN p_cobranca_id VARCHAR(36)
)
BEGIN
    SELECT 
        CASE 
            WHEN status = 'pago' OR status = 'cancelado' THEN 'nenhuma'
            ELSE 'multiplas'
        END as tipo_acao,
        CASE 
            WHEN status = 'pago' OR status = 'cancelado' THEN NULL
            ELSE 'proxima_fase,marcar_pago,cancelar'
        END as acoes_disponiveis
    FROM cobrancas
    WHERE id = p_cobranca_id;
END //
DELIMITER ;

-- Procedure: Contar Cobrancas por Status
DELIMITER //
CREATE PROCEDURE sp_contar_cobrancas_status(
    IN p_tenant_id VARCHAR(36)
)
BEGIN
    SELECT 
        status,
        COUNT(*) as total,
        SUM(valor_centavos) as valor_total_centavos
    FROM cobrancas
    WHERE tenant_id = p_tenant_id
    GROUP BY status;
END //
DELIMITER ;

-- Procedure: Obter Cobrancas Vencidas
DELIMITER //
CREATE PROCEDURE sp_cobrancas_vencidas(
    IN p_tenant_id VARCHAR(36)
)
BEGIN
    SELECT 
        id,
        processo_id,
        cliente_id,
        valor_centavos,
        status,
        fase_atual,
        data_vencimento,
        DATEDIFF(CURDATE(), DATE(data_vencimento)) as dias_vencido
    FROM cobrancas
    WHERE tenant_id = p_tenant_id
        AND status = 'pendente'
        AND data_vencimento IS NOT NULL
        AND DATE(data_vencimento) < CURDATE()
    ORDER BY data_vencimento ASC;
END //
DELIMITER ;

-- ============================================================================
-- DADOS DE TESTE (OPCIONAL)
-- ============================================================================

-- Inserir cobrança de teste
INSERT INTO cobrancas (
    id, tenant_id, user_id, processo_id, cliente_id, 
    valor_centavos, status, fase_atual, data_vencimento
) VALUES (
    UUID(), 
    'tenant-001', 
    'user-001', 
    'processo-001', 
    'cliente-001',
    50000,
    'pendente',
    0,
    DATE_ADD(NOW(), INTERVAL 30 DAY)
);

-- Inserir histórico de teste
INSERT INTO historico_cobrancas (
    id, cobranca_id, acao, status_novo, observacao
) SELECT 
    UUID(),
    id,
    'criada',
    'pendente',
    'Cobrança criada via API'
FROM cobrancas
WHERE tenant_id = 'tenant-001'
LIMIT 1;

-- ============================================================================
-- QUERIES ÚTEIS PARA MONITORAMENTO
-- ============================================================================

-- Query 1: Total de Cobrancas por Status
-- SELECT * FROM vw_cobrancas_por_status;

-- Query 2: Cobrancas Vencidas
-- SELECT * FROM vw_cobrancas_vencidas;

-- Query 3: Cobrancas Próximas de Vencer
-- SELECT * FROM vw_cobrancas_proximas_vencer;

-- Query 4: Resumo por Tenant
-- SELECT * FROM vw_resumo_cobrancas_tenant;

-- Query 5: Timeline de uma Cobrança
-- SELECT * FROM vw_timeline_cobranca WHERE cobranca_id = 'seu-id-aqui';

-- Query 6: Contar Cobrancas por Status
-- CALL sp_contar_cobrancas_status('tenant-001');

-- Query 7: Cobrancas Vencidas de um Tenant
-- CALL sp_cobrancas_vencidas('tenant-001');

-- ============================================================================
-- INFORMAÇÕES SOBRE AS FASES
-- ============================================================================
-- Fase 0: Pendente - Cobrança criada e aguardando processamento
-- Fase 1: Aguardando Pagamento - Aguardando confirmação de pagamento
-- Fase 2: Vencida - Prazo de pagamento vencido
-- Fase 3: Em Cobrança - Em processo de cobrança ativa
-- Fase 4: Pago - Cobrança paga com sucesso

-- ============================================================================
-- INFORMAÇÕES SOBRE OS STATUS
-- ============================================================================
-- pendente: Cobrança criada e não finalizada
-- pago: Cobrança paga com sucesso
-- cancelado: Cobrança cancelada

-- ============================================================================
-- INFORMAÇÕES SOBRE AS AÇÕES NO HISTÓRICO
-- ============================================================================
-- criada: Cobrança foi criada
-- fase_avancada: Fase foi avançada
-- marcado_pago: Cobrança foi marcada como paga
-- cancelada: Cobrança foi cancelada
