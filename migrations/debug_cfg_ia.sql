-- ========================================
-- Script de Debug e Teste - cfg_ia
-- ========================================

-- 1. Verificar usuário admin
SELECT 
    id as user_id, 
    tenant_id, 
    nome, 
    email, 
    role 
FROM usuarios 
WHERE email = 'admin@kealex.com';

-- 2. Verificar se existe configuração de IA
SELECT 
    tenant_id,
    user_id,
    provider,
    CASE WHEN cerebras_api_key IS NOT NULL THEN CONCAT(LEFT(cerebras_api_key, 8), '...') ELSE 'NULL' END as cerebras_key,
    CASE WHEN groq_api_key IS NOT NULL THEN CONCAT(LEFT(groq_api_key, 8), '...') ELSE 'NULL' END as groq_key,
    modelo,
    max_tokens,
    ativo,
    updated_at
FROM cfg_ia;

-- 3. Se não existir, use este INSERT (substitua os valores)
-- COPIE o tenant_id e user_id do resultado da query 1 acima

/*
INSERT INTO cfg_ia (
    tenant_id,
    user_id,
    escritorio_id,
    provider,
    cerebras_api_key,
    groq_api_key,
    modelo,
    max_tokens,
    system_prompt,
    ativo,
    updated_at
) VALUES (
    'COLE_AQUI_O_TENANT_ID',
    'COLE_AQUI_O_USER_ID',
    NULL,
    'cerebras',
    'csk-test-xxxxxxxxxxxxxxxxxxxxxxxx',
    NULL,
    'llama-3.3-70b',
    8192,
    NULL,
    1,
    NOW()
);
*/

-- 4. Ou use UPDATE se já existir
/*
UPDATE cfg_ia 
SET 
    provider = 'cerebras',
    cerebras_api_key = 'csk-test-xxxxxxxxxxxxxxxxxxxxxxxx',
    modelo = 'llama-3.3-70b',
    max_tokens = 8192,
    ativo = 1,
    updated_at = NOW()
WHERE tenant_id = 'COLE_AQUI_O_TENANT_ID';
*/

-- 5. Verificar resultado final
SELECT 
    tenant_id,
    provider,
    CASE WHEN cerebras_api_key IS NOT NULL THEN 'Configurada' ELSE 'Vazia' END as cerebras_status,
    CASE WHEN groq_api_key IS NOT NULL THEN 'Configurada' ELSE 'Vazia' END as groq_status,
    modelo,
    ativo
FROM cfg_ia;
