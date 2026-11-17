-- T8 Course-offering recommendations (FR-05, FR-06), read-only.
-- Predictor: average of the last 3 like-terms (backtested Nov 16: median error 23%
-- for undergrad Fall/Spring one year ahead; beats a linear trend, which over-predicted
-- at the 2024 enrollment peak).
-- Signals per course+term_type: recent utilization, average waitlist, direction
-- (recent 3 terms vs older terms). Confidence is LOW for 6xxx, Summer and Winter,
-- where the backtest showed enrollment follows decisions the data cannot see.
-- Recommendations are suggestions only; nothing is applied to any schedule (LIM-02, FR-09).
-- Rule order matters: REBALANCE (waitlist with empty seats) is tested before ADD SECTION,
-- so a course at low utilization with a waitlist is not told to add capacity.
WITH e AS (
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
         COUNT(*) AS sections,
         SUM(e.enrollment_count) AS enrolled,
         SUM(e.enrollment_capacity) AS capacity,
         SUM(e.waitlisted) AS waitlisted
  FROM ranked r
  JOIN primary_type p
    ON p.course_id = r.course_id AND p.term_id = r.term_id AND p.prio = r.prio
  JOIN e USING (section_id)
  JOIN academic_term t ON t.term_id = r.term_id
  GROUP BY r.course_id, t.term_type, t.term_year
),
rt AS (
  SELECT ct.*,
         ROW_NUMBER() OVER (PARTITION BY course_id, term_type
                            ORDER BY term_year DESC) AS rn
  FROM course_term ct
),
summary AS (
  SELECT course_id, term_type,
         COUNT(*)                                   AS terms_total,
         COUNT(*)    FILTER (WHERE rn <= 3)         AS recent_terms,
         ROUND(AVG(enrolled) FILTER (WHERE rn <= 3), 1) AS predicted_next,
         ROUND(AVG(enrolled) FILTER (WHERE rn > 3), 1)  AS older_avg,
         ROUND(AVG(sections) FILTER (WHERE rn <= 3), 1) AS recent_sections,
         ROUND(100.0 * SUM(enrolled) FILTER (WHERE rn <= 3)
               / NULLIF(SUM(capacity) FILTER (WHERE rn <= 3), 0), 1) AS util_pct,
         ROUND(AVG(waitlisted) FILTER (WHERE rn <= 3), 1) AS avg_waitlist
  FROM rt
  GROUP BY course_id, term_type
),
scored AS (
  SELECT s.*,
         CASE
           WHEN older_avg IS NULL THEN 'NO HISTORY'
           WHEN predicted_next > 1.10 * older_avg THEN 'GROWING'
           WHEN predicted_next < 0.90 * older_avg THEN 'DECLINING'
           ELSE 'STEADY'
         END AS direction,
         CASE
           WHEN split_part(course_id, ' ', 2) LIKE '6%'
             OR term_type IN ('Summer', 'Winter')
             OR recent_terms < 3
           THEN 'LOW' ELSE 'HIGH'
         END AS confidence
  FROM summary s
)
SELECT course_id, term_type, confidence, direction,
       predicted_next, util_pct, avg_waitlist, recent_sections,
       CASE
         WHEN util_pct IS NULL OR util_pct > 150 THEN 'CHECK DATA'
         WHEN confidence = 'LOW'                 THEN 'REVIEW MANUALLY (LOW CONFIDENCE)'
         WHEN predicted_next < 10                THEN 'LOW ENROLLMENT: REVIEW NEED'
         WHEN avg_waitlist >= 1 AND util_pct < 80 THEN 'REBALANCE SECTIONS'
         WHEN util_pct >= 95 OR avg_waitlist >= 2 THEN 'ADD SECTION'
         WHEN (direction = 'GROWING' AND util_pct >= 85)
           OR util_pct >= 90                     THEN 'WATCH: NEAR CAPACITY'
         WHEN direction = 'DECLINING' AND util_pct < 50 THEN 'REVIEW: CONSIDER FEWER SECTIONS'
         ELSE 'KEEP CURRENT SECTIONS'
       END AS recommendation,
       'Expected ~' || predicted_next || ' students (avg of last ' || recent_terms
         || ' ' || term_type || ' terms); recent utilization ' || COALESCE(util_pct::text, 'n/a')
         || '%; avg waitlist ' || avg_waitlist || '; ' || direction
         || CASE WHEN older_avg IS NOT NULL
                 THEN ' vs earlier avg ' || older_avg ELSE '' END
         || '; ~' || recent_sections || ' sections per term.' AS evidence
FROM scored
ORDER BY
  CASE WHEN util_pct IS NULL OR util_pct > 150 THEN 6
       WHEN confidence = 'LOW' THEN 5
       WHEN avg_waitlist >= 1 AND util_pct < 80 THEN 2
       WHEN util_pct >= 95 OR avg_waitlist >= 2 THEN 1
       WHEN (direction = 'GROWING' AND util_pct >= 85) OR util_pct >= 90 THEN 3
       ELSE 4 END,
  util_pct DESC NULLS LAST;
