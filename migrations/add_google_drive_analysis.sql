ALTER TABLE analise_documentos_arquivos
    ADD COLUMN drive_file_id VARCHAR(255) NULL,
    ADD COLUMN drive_web_view_link VARCHAR(1000) NULL;

CREATE TABLE IF NOT EXISTS analise_google_drive_credentials (
    id VARCHAR(36) NOT NULL PRIMARY KEY,
    tenant_id VARCHAR(36) NOT NULL,
    user_id VARCHAR(36) NOT NULL,
    encrypted_credentials TEXT NOT NULL,
    drive_folder_id VARCHAR(255) NULL,
    created_at DATETIME NOT NULL,
    updated_at DATETIME NOT NULL,
    CONSTRAINT uq_analysis_google_drive_owner UNIQUE (tenant_id, user_id),
    INDEX ix_analise_google_drive_credentials_tenant_id (tenant_id),
    INDEX ix_analise_google_drive_credentials_user_id (user_id)
);
