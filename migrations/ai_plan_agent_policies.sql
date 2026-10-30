-- Run once before deploying svc-configuracoes and svc-documentos.
ALTER TABLE agentes_ia
  ADD COLUMN owner_user_id VARCHAR(36) NULL,
  ADD COLUMN created_by VARCHAR(36) NULL,
  MODIFY COLUMN api_key TEXT NULL,
  ADD INDEX ix_agentes_ia_owner_user_id (owner_user_id);

CREATE TABLE IF NOT EXISTS ia_politicas_planos (
  tenant_id VARCHAR(36) NOT NULL,
  plan_key VARCHAR(40) NOT NULL,
  can_create_agents BOOLEAN NOT NULL DEFAULT FALSE,
  allowed_roles TEXT NOT NULL,
  max_agents INT NOT NULL DEFAULT 0,
  allowed_models TEXT NOT NULL,
  allowed_menus TEXT NOT NULL,
  monthly_token_limit INT NOT NULL DEFAULT 0,
  fallback_provider VARCHAR(50) NULL,
  fallback_model VARCHAR(190) NULL,
  updated_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
  PRIMARY KEY (tenant_id, plan_key),
  CONSTRAINT fk_ai_plan_policy_tenant FOREIGN KEY (tenant_id) REFERENCES tenants(id) ON DELETE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

CREATE TABLE IF NOT EXISTS ia_politicas_usuarios (
  tenant_id VARCHAR(36) NOT NULL,
  user_id VARCHAR(36) NOT NULL,
  can_create_agents BOOLEAN NULL,
  max_agents INT NULL,
  allowed_models TEXT NULL,
  allowed_menus TEXT NULL,
  monthly_token_limit INT NULL,
  updated_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
  PRIMARY KEY (tenant_id, user_id),
  CONSTRAINT fk_ai_user_policy_tenant FOREIGN KEY (tenant_id) REFERENCES tenants(id) ON DELETE CASCADE,
  CONSTRAINT fk_ai_user_policy_user FOREIGN KEY (user_id) REFERENCES usuarios(id) ON DELETE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

CREATE TABLE IF NOT EXISTS ia_uso_tokens (
  tenant_id VARCHAR(36) NOT NULL,
  user_id VARCHAR(36) NOT NULL,
  period CHAR(7) NOT NULL,
  tokens_used INT NOT NULL DEFAULT 0,
  updated_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
  PRIMARY KEY (tenant_id, user_id, period),
  CONSTRAINT fk_ai_token_usage_tenant FOREIGN KEY (tenant_id) REFERENCES tenants(id) ON DELETE CASCADE,
  CONSTRAINT fk_ai_token_usage_user FOREIGN KEY (user_id) REFERENCES usuarios(id) ON DELETE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;
