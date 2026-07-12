-- ============================================================================
-- SCRIPT DE OTIMIZAÇÃO - ÍNDICES E ANÁLISE
-- ============================================================================

-- ============================================================================
-- ÍNDICES ADICIONAIS PARA PERFORMANCE
-- ============================================================================

-- Índice para buscar cobrancas por tenant e data
ALTER TABLE cobrancas ADD INDEX idx_tenant_created (tenant_id, created_at DESC);

-- Índice para buscar cobrancas vencidas
ALTER TABLE cobrancas ADD INDEX idx_vencimento_status (data_vencimento, status);

-- Índice para buscar cobrancas por cliente
ALTER TABLE cobrancas ADD INDEX idx_cliente_status (cliente_id, status);

-- Índice para buscar cobrancas por processo
ALTER TABLE cobrancas ADD INDEX idx_processo_status (processo_id, status);

-- Índice para buscar histórico por data
ALTER TABLE historico_cobrancas ADD INDEX idx_created_acao (created_at DESC, acao);

-- ============================================================================
-- QUERIES DE ANÁLISE E MONITORAMENTO
-- ============================================================================

-- Query 1: Distribuição de Cobrancas por Status
SELECT 
    status,
    COUNT(*) as quantidade,
    ROUND(COUNT(*) * 100.0 / (SELECT COUNT(*) FROM cobrancas), 2) as percentual,
    SUM(valor_centavos) / 100 as valor_total_reais,
    AVG(valor_centavos) / 100 as valor_medio_reais,
    MIN(valor_centavos) / 100 as valor_minimo_reais,
    MAX(valor_centavos) / 100 as valor_maximo_reais
FROM cobrancas
GROUP BY status
ORDER BY quantidade DESC;

-- Query 2: Cobrancas por Fase
SELECT 
    fase_atual,
    CASE 
        WHEN fase_atual = 0 THEN 'Pendente'
        WHEN fase_atual = 1 THEN 'Aguardando Pagamento'
        WHEN fase_atual = 2 THEN 'Vencida'
        WHEN fase_atual = 3 THEN 'Em Cobrança'
        WHEN fase_atual = 4 THEN 'Pago'
        ELSE 'Desconhecida'
    END as fase_label,
    COUNT(*) as quantidade,
    SUM(valor_centavos) / 100 as valor_total_reais
FROM cobrancas
GROUP BY fase_atual
ORDER BY fase_atual;

-- Query 3: Cobrancas Vencidas (últimos 30 dias)
SELECT 
    id,
    processo_id,
    cliente_id,
    valor_centavos / 100 as valor_reais,
    status,
    data_vencimento,
    DATEDIFF(CURDATE(), DATE(data_vencimento)) as dias_vencido,
    created_at
FROM cobrancas
WHERE status = 'pendente'
    AND data_vencimento IS NOT NULL
    AND DATE(data_vencimento) BETWEEN DATE_SUB(CURDATE(), INTERVAL 30 DAY) AND CURDATE()
ORDER BY data_vencimento ASC;

-- Query 4: Cobrancas Próximas de Vencer (próximos 7 dias)
SELECT 
    id,
    processo_id,
    cliente_id,
    valor_centavos / 100 as valor_reais,
    status,
    data_vencimento,
    DATEDIFF(DATE(data_vencimento), CURDATE()) as dias_para_vencer
FROM cobrancas
WHERE status = 'pendente'
    AND data_vencimento IS NOT NULL
    AND DATE(data_vencimento) BETWEEN CURDATE() AND DATE_ADD(CURDATE(), INTERVAL 7 DAY)
ORDER BY data_vencimento ASC;

-- Query 5: Histórico de Ações por Tipo
SELECT 
    acao,
    COUNT(*) as total,
    MIN(created_at) as primeira_acao,
    MAX(created_at) as ultima_acao,
    DATEDIFF(MAX(created_at), MIN(created_at)) as dias_entre_acoes
FROM historico_cobrancas
GROUP BY acao
ORDER BY total DESC;

-- Query 6: Cobrancas com Mais Ações no Histórico
SELECT 
    hc.cobranca_id,
    c.processo_id,
    c.cliente_id,
    c.status,
    c.valor_centavos / 100 as valor_reais,
    COUNT(hc.id) as total_acoes,
    GROUP_CONCAT(DISTINCT hc.acao ORDER BY hc.acao) as acoes_realizadas
FROM historico_cobrancas hc
JOIN cobrancas c ON hc.cobranca_id = c.id
GROUP BY hc.cobranca_id
ORDER BY total_acoes DESC
LIMIT 20;

-- Query 7: Tempo Médio de Pagamento
SELECT 
    ROUND(AVG(DATEDIFF(DATE(data_pagamento), DATE(created_at)))) as dias_medio_pagamento,
    MIN(DATEDIFF(DATE(data_pagamento), DATE(created_at))) as dias_minimo,
    MAX(DATEDIFF(DATE(data_pagamento), DATE(created_at))) as dias_maximo,
    COUNT(*) as total_pagas
FROM cobrancas
WHERE status = 'pago' AND data_pagamento IS NOT NULL;

-- Query 8: Taxa de Conversão (Criadas vs Pagas)
SELECT 
    COUNT(DISTINCT CASE WHEN status IN ('pendente', 'pago', 'cancelado') THEN id END) as total_criadas,
    COUNT(DISTINCT CASE WHEN status = 'pago' THEN id END) as total_pagas,
    COUNT(DISTINCT CASE WHEN status = 'cancelado' THEN id END) as total_canceladas,
    ROUND(COUNT(DISTINCT CASE WHEN status = 'pago' THEN id END) * 100.0 / 
          COUNT(DISTINCT CASE WHEN status IN ('pendente', 'pago', 'cancelado') THEN id END), 2) as taxa_conversao_percentual
FROM cobrancas;

-- Query 9: Cobrancas por Tenant (Top 10)
SELECT 
    tenant_id,
    COUNT(*) as total_cobrancas,
    SUM(valor_centavos) / 100 as valor_total_reais,
    COUNT(DISTINCT CASE WHEN status = 'pago' THEN id END) as pagas,
    COUNT(DISTINCT CASE WHEN status = 'pendente' THEN id END) as pendentes,
    COUNT(DISTINCT CASE WHEN status = 'cancelado' THEN id END) as canceladas
FROM cobrancas
GROUP BY tenant_id
ORDER BY total_cobrancas DESC
LIMIT 10;

-- Query 10: Cobrancas por Usuário (Top 10)
SELECT 
    user_id,
    COUNT(*) as total_criadas,
    SUM(valor_centavos) / 100 as valor_total_reais,
    COUNT(DISTINCT CASE WHEN status = 'pago' THEN id END) as pagas,
    COUNT(DISTINCT CASE WHEN status = 'pendente' THEN id END) as pendentes
FROM cobrancas
GROUP BY user_id
ORDER BY total_criadas DESC
LIMIT 10;

-- Query 11: Cobrancas Canceladas com Motivo
SELECT 
    id,
    processo_id,
    cliente_id,
    valor_centavos / 100 as valor_reais,
    motivo_cancelamento,
    created_at,
    updated_at,
    DATEDIFF(updated_at, created_at) as dias_ate_cancelamento
FROM cobrancas
WHERE status = 'cancelado'
ORDER BY updated_at DESC;

-- Query 12: Evolução de Cobrancas por Mês
SELECT 
    DATE_TRUNC(created_at, MONTH) as mes,
    COUNT(*) as total_criadas,
    SUM(valor_centavos) / 100 as valor_total_reais,
    COUNT(DISTINCT CASE WHEN status = 'pago' THEN id END) as pagas,
    COUNT(DISTINCT CASE WHEN status = 'cancelado' THEN id END) as canceladas
FROM cobrancas
GROUP BY DATE_TRUNC(created_at, MONTH)
ORDER BY mes DESC;

-- Query 13: Cobrancas Sem Data de Vencimento
SELECT 
    id,
    processo_id,
    cliente_id,
    valor_centavos / 100 as valor_reais,
    status,
    created_at
FROM cobrancas
WHERE data_vencimento IS NULL
ORDER BY created_at DESC;

-- Query 14: Cobrancas Pagas Sem Data de Pagamento
SELECT 
    id,
    processo_id,
    cliente_id,
    valor_centavos / 100 as valor_reais,
    created_at,
    updated_at
FROM cobrancas
WHERE status = 'pago' AND data_pagamento IS NULL
ORDER BY updated_at DESC;

-- Query 15: Resumo Executivo
SELECT 
    'Total de Cobrancas' as metrica,
    COUNT(*) as valor
FROM cobrancas
UNION ALL
SELECT 'Valor Total em Reais', SUM(valor_centavos) / 100 FROM cobrancas
UNION ALL
SELECT 'Cobrancas Pagas', COUNT(*) FROM cobrancas WHERE status = 'pago'
UNION ALL
SELECT 'Cobrancas Pendentes', COUNT(*) FROM cobrancas WHERE status = 'pendente'
UNION ALL
SELECT 'Cobrancas Canceladas', COUNT(*) FROM cobrancas WHERE status = 'cancelado'
UNION ALL
SELECT 'Cobrancas Vencidas', COUNT(*) FROM cobrancas 
    WHERE status = 'pendente' AND data_vencimento IS NOT NULL AND DATE(data_vencimento) < CURDATE()
UNION ALL
SELECT 'Valor Pendente em Reais', SUM(valor_centavos) / 100 FROM cobrancas WHERE status = 'pendente'
UNION ALL
SELECT 'Valor Pago em Reais', SUM(valor_centavos) / 100 FROM cobrancas WHERE status = 'pago';

-- ============================================================================
-- TRIGGERS PARA AUDITORIA (OPCIONAL)
-- ============================================================================

-- Trigger: Registrar Atualização de Status
DELIMITER //
CREATE TRIGGER trg_cobranca_status_change
BEFORE UPDATE ON cobrancas
FOR EACH ROW
BEGIN
    IF OLD.status != NEW.status THEN
        INSERT INTO historico_cobrancas (
            id, cobranca_id, acao, status_anterior, status_novo, observacao
        ) VALUES (
            UUID(),
            NEW.id,
            'status_alterado',
            OLD.status,
            NEW.status,
            CONCAT('Status alterado de ', OLD.status, ' para ', NEW.status)
        );
    END IF;
END //
DELIMITER ;

-- Trigger: Registrar Atualização de Fase
DELIMITER //
CREATE TRIGGER trg_cobranca_fase_change
BEFORE UPDATE ON cobrancas
FOR EACH ROW
BEGIN
    IF OLD.fase_atual != NEW.fase_atual THEN
        INSERT INTO historico_cobrancas (
            id, cobranca_id, acao, fase_anterior, fase_nova, observacao
        ) VALUES (
            UUID(),
            NEW.id,
            'fase_alterada',
            OLD.fase_atual,
            NEW.fase_atual,
            CONCAT('Fase alterada de ', OLD.fase_atual, ' para ', NEW.fase_atual)
        );
    END IF;
END //
DELIMITER ;

-- ============================================================================
-- LIMPEZA E MANUTENÇÃO
-- ============================================================================

-- Procedure: Limpar Histórico Antigo (mais de 1 ano)
DELIMITER //
CREATE PROCEDURE sp_limpar_historico_antigo()
BEGIN
    DELETE FROM historico_cobrancas
    WHERE created_at < DATE_SUB(NOW(), INTERVAL 1 YEAR);
    
    SELECT ROW_COUNT() as registros_deletados;
END //
DELIMITER ;

-- Procedure: Arquivar Cobrancas Antigas
DELIMITER //
CREATE PROCEDURE sp_arquivar_cobrancas_antigas()
BEGIN
    UPDATE cobrancas
    SET status = 'arquivado'
    WHERE status = 'cancelado' 
        AND updated_at < DATE_SUB(NOW(), INTERVAL 6 MONTH);
    
    SELECT ROW_COUNT() as cobrancas_arquivadas;
END //
DELIMITER ;

-- ============================================================================
-- ESTATÍSTICAS E PERFORMANCE
-- ============================================================================

-- Verificar Tamanho das Tabelas
SELECT 
    table_name,
    ROUND(((data_length + index_length) / 1024 / 1024), 2) as tamanho_mb,
    table_rows as total_registros
FROM information_schema.TABLES
WHERE table_schema = DATABASE()
    AND table_name IN ('cobrancas', 'historico_cobrancas')
ORDER BY tamanho_mb DESC;

-- Verificar Fragmentação de Índices
SELECT 
    object_schema,
    object_name,
    index_name,
    count_read,
    count_write,
    count_delete,
    count_update
FROM performance_schema.table_io_waits_summary_by_index_usage
WHERE object_schema = DATABASE()
    AND object_name IN ('cobrancas', 'historico_cobrancas')
ORDER BY count_read DESC;
