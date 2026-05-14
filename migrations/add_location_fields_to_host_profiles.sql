-- Migration: Add location fields to host_profiles table
-- Date: 2024-12-19

-- Add location columns to host_profiles table
ALTER TABLE host_profiles 
ADD COLUMN city VARCHAR(100),
ADD COLUMN county VARCHAR(100),
ADD COLUMN address TEXT,
ADD COLUMN latitude DOUBLE PRECISION,
ADD COLUMN longitude DOUBLE PRECISION;

-- Add indexes for location-based queries
CREATE INDEX idx_host_profiles_city ON host_profiles(city);
CREATE INDEX idx_host_profiles_county ON host_profiles(county);
CREATE INDEX idx_host_profiles_coordinates ON host_profiles(latitude, longitude);

-- Update existing records to have default values
UPDATE host_profiles 
SET city = 'Unknown', 
    county = 'Unknown', 
    address = 'Address not specified',
    latitude = 0.0,
    longitude = 0.0
WHERE city IS NULL;

-- Make the fields NOT NULL after setting default values
ALTER TABLE host_profiles 
ALTER COLUMN city SET NOT NULL,
ALTER COLUMN county SET NOT NULL,
ALTER COLUMN address SET NOT NULL,
ALTER COLUMN latitude SET NOT NULL,
ALTER COLUMN longitude SET NOT NULL;
