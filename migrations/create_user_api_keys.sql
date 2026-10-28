-- User-owned AI provider credentials. Run once before deploying either backend.
CREATE TABLE IF NOT EXISTS user_api_keys (
    id VARCHAR(36) NOT NULL PRIMARY KEY,
    tenant_id VARCHAR(36) NOT NULL,
    user_id VARCHAR(36) NOT NULL,
    created_by VARCHAR(36) NOT NULL,
    provider VARCHAR(50) NOT NULL,
    model VARCHAR(190) NOT NULL,
    api_key_encrypted TEXT NOT NULL,
    is_active BOOLEAN NOT NULL DEFAULT FALSE,
    created_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    UNIQUE KEY uq_user_api_keys_user_provider_model (user_id, provider, model),
    KEY ix_user_api_keys_tenant_id (tenant_id),
    CONSTRAINT fk_user_api_keys_tenant FOREIGN KEY (tenant_id) REFERENCES tenants(id) ON DELETE CASCADE,
    CONSTRAINT fk_user_api_keys_user FOREIGN KEY (user_id) REFERENCES usuarios(id) ON DELETE CASCADE,
    CONSTRAINT fk_user_api_keys_created_by FOREIGN KEY (created_by) REFERENCES usuarios(id) ON DELETE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;
