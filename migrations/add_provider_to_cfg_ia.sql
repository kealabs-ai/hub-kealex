-- Migração: Adicionar campo provider na tabela cfg_ia
-- Data: 2025-01-XX
-- Descrição: Adiciona suporte para múltiplos providers de IA (Cerebras e Groq)

-- Adicionar coluna provider
ALTER TABLE cfg_ia 
ADD COLUMN provider VARCHAR(50) DEFAULT 'cerebras' AFTER escritorio_id;

-- Atualizar registros existentes para usar Cerebras como padrão
UPDATE cfg_ia 
SET provider = 'cerebras' 
WHERE provider IS NULL;

-- Verificar migração
SELECT tenant_id, provider, modelo, 
       CASE 
         WHEN api_key IS NOT NULL THEN 'Configurado' 
         ELSE 'Não configurado' 
       END as status_api_key
FROM cfg_ia;

-- Rollback (se necessário)
-- ALTER TABLE cfg_ia DROP COLUMN provider;
