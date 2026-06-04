-- Remove guest groups without stay dates, and newer groups that overlap an older group (same host).
-- Keeps the earliest-created group in each overlapping set.

BEGIN;

CREATE TEMP TABLE groups_to_delete (id uuid PRIMARY KEY);

INSERT INTO groups_to_delete (id)
SELECT id FROM guest_groups
WHERE check_in_date IS NULL OR check_out_date IS NULL;

INSERT INTO groups_to_delete (id)
SELECT DISTINCT newer.id
FROM guest_groups older
JOIN guest_groups newer
  ON older.host_id = newer.host_id
 AND older.id <> newer.id
 AND older.check_in_date IS NOT NULL
 AND older.check_out_date IS NOT NULL
 AND newer.check_in_date IS NOT NULL
 AND newer.check_out_date IS NOT NULL
 AND older.check_in_date::date < newer.check_out_date::date
 AND newer.check_in_date::date < older.check_out_date::date
 AND older.created_at < newer.created_at
WHERE newer.id NOT IN (SELECT id FROM groups_to_delete)
  AND older.id NOT IN (SELECT id FROM groups_to_delete)
ON CONFLICT DO NOTHING;

-- Recommendations chain
DELETE FROM recommendations
WHERE request_id IN (
  SELECT id FROM recommendation_requests WHERE guest_group_id IN (SELECT id FROM groups_to_delete)
);
DELETE FROM recommendation_sets WHERE guest_group_id IN (SELECT id FROM groups_to_delete);
DELETE FROM recommendation_requests WHERE guest_group_id IN (SELECT id FROM groups_to_delete);

-- Itineraries chain
DELETE FROM activity_votes WHERE guest_group_id IN (SELECT id FROM groups_to_delete);
DELETE FROM activity_votes
WHERE itinerary_activity_id IN (
  SELECT ia.id FROM itinerary_activities ia
  JOIN day_plans dp ON ia.day_plan_id = dp.id
  JOIN itineraries it ON dp.itinerary_id = it.id
  WHERE it.guest_group_id IN (SELECT id FROM groups_to_delete)
);
DELETE FROM itinerary_activities
WHERE day_plan_id IN (
  SELECT dp.id FROM day_plans dp
  JOIN itineraries it ON dp.itinerary_id = it.id
  WHERE it.guest_group_id IN (SELECT id FROM groups_to_delete)
);
DELETE FROM day_plans
WHERE itinerary_id IN (
  SELECT id FROM itineraries WHERE guest_group_id IN (SELECT id FROM groups_to_delete)
);
DELETE FROM itineraries WHERE guest_group_id IN (SELECT id FROM groups_to_delete);

DELETE FROM attraction_reviews WHERE guest_group_id IN (SELECT id FROM groups_to_delete);
DELETE FROM maintenance_issue_events
WHERE issue_id IN (
  SELECT id FROM maintenance_issues WHERE guest_group_id IN (SELECT id FROM groups_to_delete)
);
DELETE FROM maintenance_issues WHERE guest_group_id IN (SELECT id FROM groups_to_delete);
DELETE FROM partner_bookings WHERE guest_group_id IN (SELECT id FROM groups_to_delete);
DELETE FROM access_codes WHERE guest_group_id IN (SELECT id FROM groups_to_delete);
DELETE FROM guest_preferences WHERE guest_group_id IN (SELECT id FROM groups_to_delete);
DELETE FROM guest_evisitor_data WHERE guest_group_id IN (SELECT id FROM groups_to_delete);
DELETE FROM guest_groups WHERE id IN (SELECT id FROM groups_to_delete);

COMMIT;
