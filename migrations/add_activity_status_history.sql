ALTER TABLE activities
    ADD COLUMN status_entered_at DATETIME NULL AFTER status;

CREATE TABLE IF NOT EXISTS activity_status_history (
    id VARCHAR(36) NOT NULL PRIMARY KEY,
    activity_id VARCHAR(36) NOT NULL,
    user_id VARCHAR(36) NOT NULL,
    tenant_id VARCHAR(36) NOT NULL,
    from_status VARCHAR(36) NULL,
    to_status VARCHAR(36) NOT NULL,
    moved_at DATETIME NOT NULL,
    INDEX ix_activity_status_history_activity_moved_at (tenant_id, user_id, activity_id, moved_at)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;
