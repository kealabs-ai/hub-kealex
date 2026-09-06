# Referência SQL - Tabelas de Cobrança

## 📋 Estrutura das Tabelas

### Tabela: `cobrancas`

| Campo | Tipo | Descrição |
|-------|------|-----------|
| `id` | VARCHAR(36) | UUID único da cobrança (PK) |
| `tenant_id` | VARCHAR(36) | ID do tenant (multitenancy) |
| `user_id` | VARCHAR(36) | ID do usuário que criou |
| `processo_id` | VARCHAR(36) | ID do processo relacionado |
| `cliente_id` | VARCHAR(36) | ID do cliente |
| `valor_centavos` | INT | Valor em centavos (ex: 10000 = R$ 100,00) |
| `status` | VARCHAR(50) | Status: pendente, pago, cancelado |
| `fase_atual` | INT | Fase atual (0-4) |
| `data_vencimento` | DATETIME | Data de vencimento |
| `data_pagamento` | DATETIME | Data quando foi marcada como paga |
| `motivo_cancelamento` | VARCHAR(500) | Motivo do cancelamento |
| `created_at` | DATETIME | Data de criação |
| `updated_at` | DATETIME | Data da última atualização |

### Tabela: `historico_cobrancas`

| Campo | Tipo | Descrição |
|-------|------|-----------|
| `id` | VARCHAR(36) | UUID único do histórico (PK) |
| `cobranca_id` | VARCHAR(36) | ID da cobrança (FK) |
| `acao` | VARCHAR(100) | Tipo de ação |
| `fase_anterior` | INT | Fase anterior |
| `fase_nova` | INT | Fase nova |
| `status_anterior` | VARCHAR(50) | Status anterior |
| `status_novo` | VARCHAR(50) | Status novo |
| `observacao` | VARCHAR(500) | Observações |
| `created_at` | DATETIME | Data da ação |

## 🔍 Índices Criados

```sql
-- Tabela cobrancas
idx_tenant_id                    -- Buscar por tenant
idx_processo_id                  -- Buscar por processo
idx_cliente_id                   -- Buscar por cliente
idx_status                       -- Buscar por status
idx_fase_atual                   -- Buscar por fase
idx_created_at                   -- Ordenar por data
idx_tenant_status                -- Buscar por tenant e status
idx_tenant_processo              -- Buscar por tenant e processo
idx_tenant_created               -- Buscar por tenant e data
idx_vencimento_status            -- Buscar vencidas
idx_cliente_status               -- Buscar por cliente e status
idx_processo_status              -- Buscar por processo e status

-- Tabela historico_cobrancas
idx_cobranca_id                  -- Buscar histórico
idx_acao                         -- Buscar por tipo de ação
idx_created_at                   -- Ordenar por data
idx_cobranca_created             -- Buscar histórico por data
idx_created_acao                 -- Buscar por data e ação
```

## 📊 Views Disponíveis

### 1. `vw_cobrancas_por_status`
Resumo de cobrancas agrupadas por status com totais.

```sql
SELECT * FROM vw_cobrancas_por_status;
```

**Resultado:**
| status | total | valor_total_centavos | valor_total_reais |
|--------|-------|----------------------|-------------------|
| pendente | 45 | 450000 | 4500.00 |
| pago | 120 | 1200000 | 12000.00 |
| cancelado | 5 | 50000 | 500.00 |

### 2. `vw_cobrancas_vencidas`
Cobrancas vencidas com dias de atraso.

```sql
SELECT * FROM vw_cobrancas_vencidas;
```

### 3. `vw_cobrancas_proximas_vencer`
Cobrancas próximas de vencer (próximos 7 dias).

```sql
SELECT * FROM vw_cobrancas_proximas_vencer;
```

### 4. `vw_resumo_cobrancas_tenant`
Resumo completo por tenant.

```sql
SELECT * FROM vw_resumo_cobrancas_tenant;
```

### 5. `vw_timeline_cobranca`
Timeline completa de uma cobrança.

```sql
SELECT * FROM vw_timeline_cobranca WHERE cobranca_id = 'uuid';
```

## 🔧 Procedures Disponíveis

### 1. `sp_proximas_acoes_cobranca`
Retorna as próximas ações disponíveis para uma cobrança.

```sql
CALL sp_proximas_acoes_cobranca('cobranca-id');
```

### 2. `sp_contar_cobrancas_status`
Conta cobrancas por status de um tenant.

```sql
CALL sp_contar_cobrancas_status('tenant-id');
```

### 3. `sp_cobrancas_vencidas`
Lista cobrancas vencidas de um tenant.

```sql
CALL sp_cobrancas_vencidas('tenant-id');
```

### 4. `sp_limpar_historico_antigo`
Limpa histórico com mais de 1 ano.

```sql
CALL sp_limpar_historico_antigo();
```

### 5. `sp_arquivar_cobrancas_antigas`
Arquiva cobrancas canceladas com mais de 6 meses.

```sql
CALL sp_arquivar_cobrancas_antigas();
```

## 📈 Queries de Análise

### Distribuição por Status
```sql
SELECT status, COUNT(*) as quantidade, SUM(valor_centavos)/100 as total_reais
FROM cobrancas
GROUP BY status;
```

### Cobrancas Vencidas
```sql
SELECT id, processo_id, cliente_id, valor_centavos/100 as valor_reais, 
       DATEDIFF(CURDATE(), DATE(data_vencimento)) as dias_vencido
FROM cobrancas
WHERE status = 'pendente' AND DATE(data_vencimento) < CURDATE()
ORDER BY data_vencimento ASC;
```

### Taxa de Conversão
```sql
SELECT 
    COUNT(*) as total_criadas,
    COUNT(CASE WHEN status = 'pago' THEN 1 END) as pagas,
    ROUND(COUNT(CASE WHEN status = 'pago' THEN 1 END) * 100.0 / COUNT(*), 2) as taxa_conversao
FROM cobrancas;
```

### Tempo Médio de Pagamento
```sql
SELECT 
    ROUND(AVG(DATEDIFF(DATE(data_pagamento), DATE(created_at)))) as dias_medio
FROM cobrancas
WHERE status = 'pago' AND data_pagamento IS NOT NULL;
```

### Cobrancas por Tenant
```sql
SELECT tenant_id, COUNT(*) as total, SUM(valor_centavos)/100 as valor_total
FROM cobrancas
GROUP BY tenant_id
ORDER BY total DESC;
```

## 🔐 Constraints e Integridade

### Foreign Key
```sql
CONSTRAINT fk_historico_cobranca FOREIGN KEY (cobranca_id) 
    REFERENCES cobrancas(id) ON DELETE CASCADE
```

Quando uma cobrança é deletada, seu histórico é automaticamente removido.

## 📝 Ações no Histórico

| Ação | Descrição |
|------|-----------|
| `criada` | Cobrança foi criada |
| `fase_avancada` | Fase foi avançada |
| `marcado_pago` | Cobrança foi marcada como paga |
| `cancelada` | Cobrança foi cancelada |
| `status_alterado` | Status foi alterado (trigger) |
| `fase_alterada` | Fase foi alterada (trigger) |

## 🎯 Fases

| Fase | Label | Descrição |
|------|-------|-----------|
| 0 | Pendente | Cobrança criada e aguardando processamento |
| 1 | Aguardando Pagamento | Aguardando confirmação de pagamento |
| 2 | Vencida | Prazo de pagamento vencido |
| 3 | Em Cobrança | Em processo de cobrança ativa |
| 4 | Pago | Cobrança paga com sucesso |

## 💾 Backup e Manutenção

### Backup das Tabelas
```sql
-- Criar backup
CREATE TABLE cobrancas_backup AS SELECT * FROM cobrancas;
CREATE TABLE historico_cobrancas_backup AS SELECT * FROM historico_cobrancas;

-- Restaurar
TRUNCATE TABLE cobrancas;
INSERT INTO cobrancas SELECT * FROM cobrancas_backup;
```

### Verificar Integridade
```sql
-- Cobrancas sem histórico
SELECT c.id FROM cobrancas c
LEFT JOIN historico_cobrancas h ON c.id = h.cobranca_id
WHERE h.id IS NULL;

-- Histórico órfão
SELECT h.id FROM historico_cobrancas h
LEFT JOIN cobrancas c ON h.cobranca_id = c.id
WHERE c.id IS NULL;
```

## 🚀 Performance

### Tamanho das Tabelas
```sql
SELECT table_name, ROUND(((data_length + index_length) / 1024 / 1024), 2) as tamanho_mb
FROM information_schema.TABLES
WHERE table_schema = DATABASE()
AND table_name IN ('cobrancas', 'historico_cobrancas');
```

### Queries Lentas
```sql
-- Ativar log de queries lentas
SET GLOBAL slow_query_log = 'ON';
SET GLOBAL long_query_time = 2;

-- Ver queries lentas
SELECT * FROM mysql.slow_log;
```

## 📚 Exemplos de Uso

### Criar Cobrança
```sql
INSERT INTO cobrancas (
    id, tenant_id, user_id, processo_id, cliente_id,
    valor_centavos, status, fase_atual, data_vencimento
) VALUES (
    UUID(), 'tenant-001', 'user-001', 'processo-001', 'cliente-001',
    50000, 'pendente', 0, DATE_ADD(NOW(), INTERVAL 30 DAY)
);
```

### Avançar Fase
```sql
UPDATE cobrancas
SET fase_atual = 1, updated_at = NOW()
WHERE id = 'cobranca-id';

INSERT INTO historico_cobrancas (
    id, cobranca_id, acao, fase_anterior, fase_nova, observacao
) VALUES (
    UUID(), 'cobranca-id', 'fase_avancada', 0, 1, 'Fase avançada'
);
```

### Marcar como Pago
```sql
UPDATE cobrancas
SET status = 'pago', fase_atual = 4, data_pagamento = NOW(), updated_at = NOW()
WHERE id = 'cobranca-id';

INSERT INTO historico_cobrancas (
    id, cobranca_id, acao, status_anterior, status_novo, observacao
) VALUES (
    UUID(), 'cobranca-id', 'marcado_pago', 'pendente', 'pago', 'Pagamento recebido'
);
```

### Cancelar Cobrança
```sql
UPDATE cobrancas
SET status = 'cancelado', motivo_cancelamento = 'Motivo aqui', updated_at = NOW()
WHERE id = 'cobranca-id';

INSERT INTO historico_cobrancas (
    id, cobranca_id, acao, status_anterior, status_novo, observacao
) VALUES (
    UUID(), 'cobranca-id', 'cancelada', 'pendente', 'cancelado', 'Motivo aqui'
);
```
