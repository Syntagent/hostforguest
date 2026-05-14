-- Link guest groups to the host's accommodation profile (host_profiles).
-- Run against PostgreSQL after deploy.

ALTER TABLE guest_groups
  ADD COLUMN IF NOT EXISTS host_profile_id UUID NULL
  REFERENCES host_profiles (id) ON DELETE SET NULL;

CREATE INDEX IF NOT EXISTS idx_guest_groups_host_profile_id ON guest_groups (host_profile_id);

UPDATE guest_groups gg
SET host_profile_id = hp.id
FROM host_profiles hp
WHERE hp.host_id = gg.host_id
  AND gg.host_profile_id IS NULL;
