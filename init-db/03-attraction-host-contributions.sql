-- Persist host tips/stories per attraction (used by /attractions/.../contributions).
CREATE TABLE IF NOT EXISTS attraction_host_contributions (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    attraction_id UUID NOT NULL REFERENCES attractions (id) ON DELETE CASCADE,
    host_id UUID NOT NULL REFERENCES hosts (id) ON DELETE CASCADE,
    contribution_type VARCHAR(50) NOT NULL,
    title VARCHAR(200) NOT NULL,
    content TEXT NOT NULL,
    is_public BOOLEAN NOT NULL DEFAULT TRUE,
    language VARCHAR(10) NOT NULL DEFAULT 'en',
    created_at TIMESTAMP WITHOUT TIME ZONE NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMP WITHOUT TIME ZONE NOT NULL DEFAULT NOW()
);
CREATE INDEX IF NOT EXISTS ix_attraction_host_contributions_attraction
    ON attraction_host_contributions (attraction_id);
CREATE INDEX IF NOT EXISTS ix_attraction_host_contributions_host
    ON attraction_host_contributions (host_id);
