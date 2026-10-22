-- MySQL: permite cadastros de Departamento Jurídico como papel próprio.
ALTER TABLE usuarios
    MODIFY COLUMN role ENUM('admin', 'escritorio', 'advogado', 'juridico', 'cliente') NOT NULL;