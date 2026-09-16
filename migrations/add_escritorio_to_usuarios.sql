-- Migration: adicionar escritorio_id na tabela usuarios para suporte a modalidade
ALTER TABLE usuarios
    ADD COLUMN IF NOT EXISTS escritorio_id VARCHAR(36) NULL
        COMMENT 'NULL = autônomo | UUID = associado a escritório';

-- Index para consultas por escritório
CREATE INDEX IF NOT EXISTS idx_usuarios_escritorio ON usuarios (escritorio_id);
