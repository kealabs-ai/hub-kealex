ALTER TABLE tenants
  ADD COLUMN subscription_cycle VARCHAR(20) NULL,
  ADD COLUMN subscription_expires_at DATETIME NULL,
  ADD COLUMN last_paid_payment_id VARCHAR(80) NULL;
