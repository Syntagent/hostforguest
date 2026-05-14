-- Migration: Create e-visitor data table
-- Date: 2025-08-27
-- Description: Add table for storing individual guest e-visitor registration data for Croatia

-- Create e-visitor data table
CREATE TABLE IF NOT EXISTS guest_evisitor_data (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    guest_group_id UUID NOT NULL REFERENCES guest_groups(id) ON DELETE CASCADE,
    
    -- Personal Information (Required for e-visitor)
    first_name VARCHAR(100) NOT NULL,
    last_name VARCHAR(100) NOT NULL,
    date_of_birth TIMESTAMP NOT NULL,
    nationality VARCHAR(100) NOT NULL,
    
    -- ID Information
    id_type VARCHAR(20) NOT NULL, -- 'passport' or 'id_card'
    id_number VARCHAR(100) NOT NULL, -- Passport or ID number
    id_issuing_country VARCHAR(100) NOT NULL,
    id_expiry_date TIMESTAMP,
    
    -- Address Information
    address_line1 VARCHAR(255),
    address_line2 VARCHAR(255),
    city VARCHAR(100),
    state_province VARCHAR(100),
    postal_code VARCHAR(20),
    country VARCHAR(100),
    
    -- Stay Information
    arrival_date TIMESTAMP NOT NULL,
    departure_date TIMESTAMP NOT NULL,
    
    -- Contact Information
    email VARCHAR(255),
    phone VARCHAR(20),
    
    -- E-visitor Status
    evisitor_registered BOOLEAN DEFAULT FALSE,
    evisitor_registration_date TIMESTAMP,
    evisitor_confirmation_number VARCHAR(100),
    
    -- Metadata
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Create indexes for better performance
CREATE INDEX IF NOT EXISTS idx_guest_evisitor_data_group_id ON guest_evisitor_data(guest_group_id);
CREATE INDEX IF NOT EXISTS idx_guest_evisitor_data_registered ON guest_evisitor_data(evisitor_registered);
CREATE INDEX IF NOT EXISTS idx_guest_evisitor_data_arrival ON guest_evisitor_data(arrival_date);
CREATE INDEX IF NOT EXISTS idx_guest_evisitor_data_departure ON guest_evisitor_data(departure_date);

-- Add comments for documentation
COMMENT ON TABLE guest_evisitor_data IS 'Individual guest e-visitor registration data for Croatia';
COMMENT ON COLUMN guest_evisitor_data.id_type IS 'Type of identification: passport or id_card';
COMMENT ON COLUMN guest_evisitor_data.evisitor_registered IS 'Whether the guest has been registered with Croatian e-visitor system';
COMMENT ON COLUMN guest_evisitor_data.evisitor_confirmation_number IS 'Confirmation number from Croatian e-visitor registration';
