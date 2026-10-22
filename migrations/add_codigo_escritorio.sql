-- Códigos de convite dos escritórios. Compatível com MySQL 8+.
ALTER TABLE escritorios ADD COLUMN codigo VARCHAR(16) NULL;

-- Gera códigos determinísticos para registros antigos usando parte do UUID.
UPDATE escritorios
SET codigo = CONCAT('KX-', UPPER(SUBSTRING(REPLACE(id, '-', ''), 1, 12)))
WHERE codigo IS NULL;

ALTER TABLE escritorios MODIFY COLUMN codigo VARCHAR(16) NOT NULL;
CREATE UNIQUE INDEX uq_escritorios_codigo ON escritorios (codigo);