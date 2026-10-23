-- Store the association code used to link the user to an office.
ALTER TABLE usuarios
    ADD COLUMN codigo VARCHAR(16) NULL
        COMMENT 'Office association code used by this user';
