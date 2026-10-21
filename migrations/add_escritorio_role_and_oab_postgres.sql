-- PostgreSQL variant of add_escritorio_role_and_oab.sql.
ALTER TYPE role_enum_auth ADD VALUE IF NOT EXISTS 'escritorio';

ALTER TABLE usuarios
    ADD COLUMN IF NOT EXISTS oab VARCHAR(50) NULL;

CREATE INDEX IF NOT EXISTS idx_usuarios_escritorio_role_ativo
    ON usuarios (escritorio_id, role, ativo);
