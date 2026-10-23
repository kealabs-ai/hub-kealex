-- Renomeia a coluna de vínculo da tabela criada pela migração anterior.
ALTER TABLE usuarios_chaves_publicas
    RENAME COLUMN usuario_id TO user_id;

-- Mantém o nome do índice alinhado ao novo nome da coluna.
ALTER TABLE usuarios_chaves_publicas
    DROP INDEX ix_usuarios_chaves_publicas_usuario,
    ADD INDEX ix_usuarios_chaves_publicas_user_id (user_id);
