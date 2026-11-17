-- T7 Course demand analysis (FR-04), read-only.
-- Rules: one component per course per term (Discussion first), total enrollment per term,
-- future terms (0 enrolled) left out, like terms compared, weighted utilization.
-- Thresholds (team to confirm): INCREASING/DECREASING = slope beyond 5% of average per year;
-- LOW ENROLLMENT = average under 10; CHECK DATA = no capacity or enrolled > 150% of capacity.
WITH e AS (
  SELECT section_id, enrollment_count, enrollment_capacity
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
         COUNT(*) AS sections,
         SUM(e.enrollment_count) AS enrolled,
         SUM(e.enrollment_capacity) AS capacity
  FROM ranked r
  JOIN primary_type p
    ON p.course_id = r.course_id AND p.term_id = r.term_id AND p.prio = r.prio
  JOIN e USING (section_id)
  JOIN academic_term t ON t.term_id = r.term_id
  GROUP BY r.course_id, t.term_type, t.term_year
)
SELECT course_id, term_type,
       COUNT(*) AS terms,
       ROUND(AVG(enrolled), 1) AS avg_enrolled_per_term,
       ROUND(100.0 * SUM(enrolled) / NULLIF(SUM(capacity), 0), 1) AS utilization_pct,
       ROUND(regr_slope(enrolled, term_year)::numeric, 1) AS slope_per_year,
       CASE
         WHEN COUNT(*) < 3 THEN 'NOT ENOUGH DATA'
         WHEN AVG(enrolled) < 10 THEN 'LOW ENROLLMENT'
         WHEN SUM(capacity) IS NULL OR SUM(capacity) = 0
              OR SUM(enrolled) > 1.5 * SUM(capacity) THEN 'CHECK DATA'
         WHEN regr_slope(enrolled, term_year) >  0.05 * AVG(enrolled) THEN 'INCREASING'
         WHEN regr_slope(enrolled, term_year) < -0.05 * AVG(enrolled) THEN 'DECREASING'
         ELSE 'STABLE'
       END AS trend
FROM course_term
GROUP BY course_id, term_type
ORDER BY course_id, term_type;
