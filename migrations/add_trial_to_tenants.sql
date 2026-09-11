-- ============================================================
-- Migration: adicionar controle de trial na tabela tenants
-- ============================================================

ALTER TABLE tenants
    ADD COLUMN IF NOT EXISTS plano           VARCHAR(20)  NOT NULL DEFAULT 'trial'
        COMMENT 'trial | starter | professional | enterprise',
    ADD COLUMN IF NOT EXISTS trial_started_at DATETIME    NULL
        COMMENT 'Data de início do trial (NULL = nunca iniciou)',
    ADD COLUMN IF NOT EXISTS trial_expires_at DATETIME    NULL
        COMMENT 'Data de expiração do trial (calculada: trial_started_at + 7 dias)';

-- Preenche trial_started_at para tenants existentes que ainda não têm
UPDATE tenants
SET
    trial_started_at = created_at,
    trial_expires_at = DATE_ADD(created_at, INTERVAL 7 DAY)
WHERE trial_started_at IS NULL AND plano = 'trial';

-- Index para consultas de expiração
CREATE INDEX IF NOT EXISTS idx_tenants_trial_expires ON tenants (trial_expires_at);
