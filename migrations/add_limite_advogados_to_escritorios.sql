-- Add the office user quota and enforce the office association.
ALTER TABLE escritorios
    ADD COLUMN limite_advogados INTEGER NOT NULL DEFAULT 3;

-- Clear stale references before adding the foreign key.
UPDATE usuarios u
LEFT JOIN escritorios e ON e.id = u.escritorio_id
SET u.escritorio_id = NULL
WHERE u.escritorio_id IS NOT NULL AND e.id IS NULL;

ALTER TABLE usuarios
    ADD CONSTRAINT fk_usuarios_escritorio
    FOREIGN KEY (escritorio_id) REFERENCES escritorios(id) ON DELETE SET NULL;
