-- MySQL migration: enables dedicated office login accounts and lawyer registration details.
-- Run before deploying svc-auth, svc-usuarios and svc-escritorios.
ALTER TABLE usuarios
    MODIFY COLUMN role ENUM('admin', 'escritorio', 'advogado', 'cliente') NOT NULL;

ALTER TABLE usuarios
    ADD COLUMN oab VARCHAR(50) NULL;

CREATE INDEX idx_usuarios_escritorio_role_ativo
    ON usuarios (escritorio_id, role, ativo);
