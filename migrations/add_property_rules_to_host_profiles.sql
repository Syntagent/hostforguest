-- House rules, check-in/out times, and practical stay info for guest-facing guide.
ALTER TABLE host_profiles
  ADD COLUMN IF NOT EXISTS property_rules JSONB NOT NULL DEFAULT '{}'::jsonb;
