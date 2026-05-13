-- Adicionar coluna ativo na tabela cfg_ia se não existir
ALTER TABLE cfg_ia ADD COLUMN IF NOT EXISTS ativo TINYINT(1) DEFAULT 1;