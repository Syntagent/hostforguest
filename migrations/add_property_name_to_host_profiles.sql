-- Migration: Add property_name column to host_profiles table
-- Date: 2024-12-19
-- Description: Add property_name field to store the name of the host's property

-- Add the property_name column
ALTER TABLE host_profiles 
ADD COLUMN property_name VARCHAR(255);

-- Create an index on property_name for better query performance
CREATE INDEX idx_host_profiles_property_name ON host_profiles(property_name);

-- Update existing records to set a default property name based on business_name or first_name
UPDATE host_profiles 
SET property_name = COALESCE(
    (SELECT business_name FROM hosts WHERE hosts.id = host_profiles.host_id),
    (SELECT first_name FROM hosts WHERE hosts.id = host_profiles.host_id) || '''s Property'
)
WHERE property_name IS NULL;

-- Make the column NOT NULL after setting default values
ALTER TABLE host_profiles 
ALTER COLUMN property_name SET NOT NULL;
