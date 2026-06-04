-- Migration: Host compliance checklist (obveze iznajmljivača)
-- Date: 2026-05-29

CREATE TABLE IF NOT EXISTS host_compliance_settings (
    host_id UUID PRIMARY KEY REFERENCES hosts(id) ON DELETE CASCADE,
    scenarios JSONB NOT NULL DEFAULT '{}',
    catalog_version VARCHAR(32),
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS host_compliance_items (
    host_id UUID NOT NULL REFERENCES hosts(id) ON DELETE CASCADE,
    item_id VARCHAR(64) NOT NULL,
    status VARCHAR(20) NOT NULL DEFAULT 'missing',
    notes TEXT,
    completed_at TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    PRIMARY KEY (host_id, item_id)
);

CREATE INDEX IF NOT EXISTS idx_host_compliance_items_host ON host_compliance_items(host_id);

COMMENT ON TABLE host_compliance_settings IS 'Per-host compliance scenario flags and catalog version';
COMMENT ON TABLE host_compliance_items IS 'Per-host checklist item status for state obligations';
