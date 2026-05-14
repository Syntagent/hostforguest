-- Align guest_groups with ORM (host_profile_id); safe for existing volumes.
ALTER TABLE guest_groups ADD COLUMN IF NOT EXISTS host_profile_id UUID;
CREATE INDEX IF NOT EXISTS ix_guest_groups_host_profile_id ON guest_groups (host_profile_id);
