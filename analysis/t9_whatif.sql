-- T9 What-if scenario (FR-07, FR-08), read-only.
-- Scenario: "what if COURSE got EXTRA_SEATS more capacity per term?"
-- Recomputes the T8 signals with the changed input and shows them
-- against the baseline. Nothing is written; the baseline never changes (DR, LIM-02).
WITH params AS (
  SELECT 'CSE 4550'::text AS course,      -- <-- change these two values per scenario
         30::int          AS extra_seats
),
e AS (
  SELECT section_id, enrollment_count, enrollment_capacity,
         COALESCE(waitlist_count, waitlist_students, 0) AS waitlisted
  FROM section_enrollment
),
past_terms AS (
  SELECT cs.term_id
  FROM course_section cs JOIN e USING (section_id)
  GROUP BY cs.term_id
  HAVING SUM(e.enrollment_count) > 0
),
ranked AS (
  SELECT cs.*,
         CASE cs.class_type
           WHEN 'Discussion' THEN 1 WHEN 'Lecture' THEN 2
           WHEN 'Seminar' THEN 3 WHEN 'Activity' THEN 4
           WHEN 'Laboratory' THEN 5 WHEN 'Supervision' THEN 6
           ELSE 7 END AS prio
  FROM course_section cs
  WHERE cs.term_id IN (SELECT term_id FROM past_terms)
),
primary_type AS (
  SELECT course_id, term_id, MIN(prio) AS prio
  FROM ranked GROUP BY course_id, term_id
),
course_term AS (
  SELECT r.course_id, t.term_type, t.term_year,
         SUM(e.enrollment_count) AS enrolled,
         SUM(e.enrollment_capacity) AS capacity,
         SUM(e.waitlisted) AS waitlisted
  FROM ranked r
  JOIN primary_type p
    ON p.course_id = r.course_id AND p.term_id = r.term_id AND p.prio = r.prio
  JOIN e USING (section_id)
  JOIN academic_term t ON t.term_id = r.term_id
  WHERE r.course_id = (SELECT course FROM params)
  GROUP BY r.course_id, t.term_type, t.term_year
),
rt AS (
  SELECT ct.*,
         ROW_NUMBER() OVER (PARTITION BY term_type ORDER BY term_year DESC) AS rn
  FROM course_term ct
),
both_cases AS (
  SELECT 'baseline' AS run, term_type,
         ROUND(AVG(enrolled) FILTER (WHERE rn <= 3), 1) AS predicted_next,
         ROUND(100.0 * SUM(enrolled) FILTER (WHERE rn <= 3)
               / NULLIF(SUM(capacity) FILTER (WHERE rn <= 3), 0), 1) AS util_pct,
         ROUND(AVG(waitlisted) FILTER (WHERE rn <= 3), 1) AS avg_waitlist
  FROM rt GROUP BY term_type
  UNION ALL
  SELECT 'scenario: +' || (SELECT extra_seats FROM params) || ' seats', term_type,
         ROUND(AVG(enrolled) FILTER (WHERE rn <= 3), 1),
         ROUND(100.0 * SUM(enrolled) FILTER (WHERE rn <= 3)
               / NULLIF(SUM(capacity + (SELECT extra_seats FROM params))
                        FILTER (WHERE rn <= 3), 0), 1),
         ROUND(AVG(waitlisted) FILTER (WHERE rn <= 3), 1)
  FROM rt GROUP BY term_type
)
SELECT (SELECT course FROM params) AS course_id, term_type, run,
       predicted_next, util_pct, avg_waitlist,
       CASE
         WHEN util_pct IS NULL OR util_pct > 150     THEN 'CHECK DATA'
         WHEN avg_waitlist >= 1 AND util_pct < 80    THEN 'REBALANCE SECTIONS'
         WHEN util_pct >= 95 OR avg_waitlist >= 2    THEN 'ADD SECTION'
         WHEN util_pct >= 90                         THEN 'WATCH: NEAR CAPACITY'
         ELSE 'KEEP CURRENT SECTIONS'
       END AS recommendation
FROM both_cases
ORDER BY term_type, run;
