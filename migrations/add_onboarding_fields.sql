-- Migration to add onboarding and guest access fields
-- Run this to update existing database schema

-- Add guest access fields to hosts table
ALTER TABLE hosts 
ADD COLUMN IF NOT EXISTS guest_access_code VARCHAR(10) UNIQUE,
ADD COLUMN IF NOT EXISTS onboarding_completed BOOLEAN DEFAULT FALSE;

-- Add index for faster guest access lookups
CREATE INDEX IF NOT EXISTS idx_hosts_guest_access_code ON hosts(guest_access_code);

-- Add onboarding fields to host_profiles table  
ALTER TABLE host_profiles
ADD COLUMN IF NOT EXISTS location_story TEXT,
ADD COLUMN IF NOT EXISTS google_verified BOOLEAN DEFAULT FALSE,
ADD COLUMN IF NOT EXISTS onboarding_completed BOOLEAN DEFAULT FALSE,
ADD COLUMN IF NOT EXISTS onboarding_completed_at VARCHAR(50),
ADD COLUMN IF NOT EXISTS ai_generated_content BOOLEAN DEFAULT FALSE;

-- Update existing profiles to have default values
UPDATE host_profiles 
SET google_verified = FALSE, 
    onboarding_completed = FALSE,
    ai_generated_content = FALSE
WHERE google_verified IS NULL 
   OR onboarding_completed IS NULL 
   OR ai_generated_content IS NULL;
