-- Renomeia a coluna de vínculo da tabela criada pela migração anterior.
ALTER TABLE usuarios_chaves_publicas
    RENAME COLUMN usuario_id TO user_id;
