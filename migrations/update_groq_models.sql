-- Script para atualizar modelos Groq descontinuados
-- Execute este script no banco de dados MySQL

-- Verificar configurações atuais
SELECT 
    tenant_id,
    provider,
    modelo,
    ativo,
    updated_at
FROM cfg_ia 
WHERE provider = 'groq';

-- Atualizar modelos descontinuados do Groq
UPDATE cfg_ia 
SET 
    modelo = CASE 
        WHEN modelo = 'mixtral-8x7b-32768' THEN 'llama-3.1-70b-versatile'
        WHEN modelo = 'llama2-70b-4096' THEN 'llama-3.1-70b-versatile'
        WHEN modelo = 'gemma-7b-it' THEN 'gemma2-9b-it'
        ELSE modelo
    END,
    updated_at = NOW()
WHERE provider = 'groq' 
AND modelo IN ('mixtral-8x7b-32768', 'llama2-70b-4096', 'gemma-7b-it');

-- Verificar resultado da atualização
SELECT 
    tenant_id,
    provider,
    modelo,
    ativo,
    updated_at
FROM cfg_ia 
WHERE provider = 'groq';

-- Modelos disponíveis por provider (para referência):
-- 
-- Cerebras:
-- - llama-3.3-70b
-- - llama-3.1-70b  
-- - llama-3.1-8b
--
-- Groq:
-- - llama-3.3-70b-versatile
-- - llama-3.1-70b-versatile
-- - llama-3.1-8b-instant
-- - llama-3.2-90b-text-preview
-- - llama-3.2-11b-text-preview
-- - llama-3.2-3b-preview
-- - llama-3.2-1b-preview
-- - gemma2-9b-it
-- - gemma-7b-it