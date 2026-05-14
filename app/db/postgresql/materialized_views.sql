-- Materialized views for performance optimization
-- Pre-computed aggregations to reduce query load

-- Materialized view for host statistics
CREATE MATERIALIZED VIEW IF NOT EXISTS host_statistics AS
SELECT
    h.id AS host_id,
    h.city,
    h.region,
    COUNT(DISTINCT gg.id) AS total_guest_groups,
    COUNT(DISTINCT a.id) AS total_attractions,
    COUNT(DISTINCT rs.id) AS total_recommendation_sets,
    AVG(rs.overall_satisfaction) AS avg_satisfaction,
    SUM(pb.booking_amount) AS total_revenue,
    SUM(pb.commission_amount) AS total_commission
FROM hosts h
LEFT JOIN guest_groups gg ON gg.host_id = h.id
LEFT JOIN attractions a ON a.created_by_host_id = h.id
LEFT JOIN recommendation_sets rs ON rs.host_id = h.id
LEFT JOIN partner_bookings pb ON pb.host_id = h.id AND pb.status = 'confirmed'
GROUP BY h.id, h.city, h.region;

-- Create index on materialized view
CREATE INDEX IF NOT EXISTS idx_host_statistics_host_id ON host_statistics(host_id);
CREATE INDEX IF NOT EXISTS idx_host_statistics_city ON host_statistics(city);

-- Materialized view for attraction popularity
CREATE MATERIALIZED VIEW IF NOT EXISTS attraction_popularity AS
SELECT
    a.id AS attraction_id,
    a.name,
    a.city,
    a.attraction_type,
    COUNT(DISTINCT r.id) AS total_recommendations,
    COUNT(DISTINCT ar.id) AS total_reviews,
    AVG(ar.rating) AS avg_rating,
    COUNT(DISTINCT CASE WHEN r.accepted = true THEN r.id END) AS accepted_recommendations
FROM attractions a
LEFT JOIN recommendations r ON r.attraction_id = a.id
LEFT JOIN attraction_reviews ar ON ar.attraction_id = a.id AND ar.status = 'approved'
GROUP BY a.id, a.name, a.city, a.attraction_type;

-- Create index on materialized view
CREATE INDEX IF NOT EXISTS idx_attraction_popularity_attraction_id ON attraction_popularity(attraction_id);
CREATE INDEX IF NOT EXISTS idx_attraction_popularity_city ON attraction_popularity(city);

-- Function to refresh materialized views
CREATE OR REPLACE FUNCTION refresh_materialized_views()
RETURNS void AS $$
BEGIN
    REFRESH MATERIALIZED VIEW CONCURRENTLY host_statistics;
    REFRESH MATERIALIZED VIEW CONCURRENTLY attraction_popularity;
END;
$$ LANGUAGE plpgsql;

