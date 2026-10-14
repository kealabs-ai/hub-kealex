-- Campos usados para controlar o ciclo e a validade da assinatura.
-- Pode ser executado novamente sem erro se as colunas já existirem.
ALTER TABLE tenants
  ADD COLUMN IF NOT EXISTS subscription_cycle VARCHAR(20) NULL,
  ADD COLUMN IF NOT EXISTS subscription_expires_at DATETIME NULL,
  ADD COLUMN IF NOT EXISTS last_paid_payment_id VARCHAR(80) NULL;
