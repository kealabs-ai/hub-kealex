-- Script para inserir configuração de IA ativa para testes
-- Execute este script no banco de dados MySQL

-- Primeiro, vamos verificar se já existe uma configuração
SELECT * FROM cfg_ia;

-- Se não existir, vamos buscar o tenant_id e user_id do admin
SELECT id as user_id, tenant_id FROM usuarios WHERE email = 'admin@kealex.com' LIMIT 1;

-- Inserir configuração de IA com Cerebras (substitua os valores abaixo)
-- IMPORTANTE: Substitua 'SEU_TENANT_ID' e 'SEU_USER_ID' pelos valores retornados acima
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
    'SEU_TENANT_ID',  -- Substitua pelo tenant_id do admin
    'SEU_USER_ID',    -- Substitua pelo user_id do admin
    NULL,
    'cerebras',
    'csk-test-key-xxxxxxxxxxxxxxxxxxxxxxxx',  -- Substitua por uma chave real
    NULL,
    'llama-3.3-70b',
    8192,
    NULL,
    1,  -- ativo = TRUE
    NOW()
)
ON DUPLICATE KEY UPDATE
    provider = 'cerebras',
    cerebras_api_key = 'csk-test-key-xxxxxxxxxxxxxxxxxxxxxxxx',
    modelo = 'llama-3.3-70b',
    max_tokens = 8192,
    ativo = 1,
    updated_at = NOW();

-- Verificar se foi inserido corretamente
SELECT 
    tenant_id,
    user_id,
    provider,
    CASE 
        WHEN cerebras_api_key IS NOT NULL THEN 'Configurada'
        ELSE 'Vazia'
    END as cerebras_key_status,
    CASE 
        WHEN groq_api_key IS NOT NULL THEN 'Configurada'
        ELSE 'Vazia'
    END as groq_key_status,
    modelo,
    max_tokens,
    ativo,
    updated_at
FROM cfg_ia;
