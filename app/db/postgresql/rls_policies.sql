-- Row-Level Security (RLS) policies for multi-tenant security
-- PostgreSQL RLS policies to ensure data isolation between hosts

-- Enable RLS on hosts table
ALTER TABLE hosts ENABLE ROW LEVEL SECURITY;

-- Policy: Hosts can only see their own data
CREATE POLICY host_isolation_policy ON hosts
    FOR ALL
    USING (id = current_setting('app.current_host_id', true)::uuid);

-- Enable RLS on guest_groups table
ALTER TABLE guest_groups ENABLE ROW LEVEL SECURITY;

-- Policy: Hosts can only see their own guest groups
CREATE POLICY guest_group_isolation_policy ON guest_groups
    FOR ALL
    USING (host_id = current_setting('app.current_host_id', true)::uuid);

-- Enable RLS on attractions table
ALTER TABLE attractions ENABLE ROW LEVEL SECURITY;

-- Policy: Hosts can only see their own attractions
CREATE POLICY attraction_isolation_policy ON attractions
    FOR ALL
    USING (created_by_host_id = current_setting('app.current_host_id', true)::uuid);

-- Enable RLS on recommendations table
ALTER TABLE recommendations ENABLE ROW LEVEL SECURITY;

-- Policy: Hosts can only see recommendations for their guest groups
CREATE POLICY recommendation_isolation_policy ON recommendations
    FOR ALL
    USING (
        EXISTS (
            SELECT 1 FROM guest_groups
            WHERE guest_groups.id = recommendations.guest_group_id
            AND guest_groups.host_id = current_setting('app.current_host_id', true)::uuid
        )
    );

-- Enable RLS on recommendation_sets table
ALTER TABLE recommendation_sets ENABLE ROW LEVEL SECURITY;

-- Policy: Hosts can only see their own recommendation sets
CREATE POLICY recommendation_set_isolation_policy ON recommendation_sets
    FOR ALL
    USING (host_id = current_setting('app.current_host_id', true)::uuid);

-- Enable RLS on partner_bookings table
ALTER TABLE partner_bookings ENABLE ROW LEVEL SECURITY;

-- Policy: Hosts can only see their own bookings
CREATE POLICY booking_isolation_policy ON partner_bookings
    FOR ALL
    USING (host_id = current_setting('app.current_host_id', true)::uuid);

-- Enable RLS on host_subscriptions table
ALTER TABLE host_subscriptions ENABLE ROW LEVEL SECURITY;

-- Policy: Hosts can only see their own subscriptions
CREATE POLICY subscription_isolation_policy ON host_subscriptions
    FOR ALL
    USING (host_id = current_setting('app.current_host_id', true)::uuid);

-- Function to set current host ID for RLS
CREATE OR REPLACE FUNCTION set_current_host_id(host_id uuid)
RETURNS void AS $$
BEGIN
    PERFORM set_config('app.current_host_id', host_id::text, false);
END;
$$ LANGUAGE plpgsql;

