-- PostgreSQL: permite cadastros de Departamento Jurídico como papel próprio.
ALTER TYPE role_enum_auth ADD VALUE IF NOT EXISTS 'juridico';