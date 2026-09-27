ALTER TABLE tenants
  ADD COLUMN IF NOT EXISTS asaas_customer_id VARCHAR(80) NULL,
  ADD COLUMN IF NOT EXISTS billing_cpf_cnpj VARCHAR(20) NULL,
  ADD COLUMN IF NOT EXISTS billing_phone VARCHAR(30) NULL,
  ADD COLUMN IF NOT EXISTS billing_mobile_phone VARCHAR(30) NULL,
  ADD COLUMN IF NOT EXISTS asaas_subscription_id VARCHAR(80) NULL,
  ADD COLUMN IF NOT EXISTS subscription_plan VARCHAR(20) NULL,
  ADD COLUMN IF NOT EXISTS subscription_status VARCHAR(20) NOT NULL DEFAULT 'trialing',
  ADD COLUMN IF NOT EXISTS next_due_date VARCHAR(10) NULL;

CREATE UNIQUE INDEX IF NOT EXISTS uq_tenants_asaas_subscription
  ON tenants (asaas_subscription_id);

CREATE TABLE  asaas_webhook_events (
  id VARCHAR(100) NOT NULL PRIMARY KEY,
  event VARCHAR(80) NOT NULL,
  received_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP
);

-- Compatibilidade com cadastros antigos: o pre-cadastro era salvo como
-- pendente/inativo e impedia o titular de autenticar para regularizar a conta.
-- Preserva a data original; trials já vencidos continuam vencidos.
UPDATE usuarios u
JOIN tenants t ON t.id = u.tenant_id
SET u.ativo = TRUE
WHERE t.plano = 'pendente';

UPDATE tenants
SET plano = 'trial',
    trial_started_at = COALESCE(trial_started_at, created_at),
    trial_expires_at = COALESCE(trial_expires_at, DATE_ADD(created_at, INTERVAL 7 DAY)),
    ativo = TRUE
WHERE plano = 'pendente';

UPDATE tenants
SET subscription_status = CASE
  WHEN plano = 'trial' THEN 'trialing'
  WHEN plano IN ('starter', 'professional', 'enterprise') THEN 'active'
  ELSE 'inactive'
END;
