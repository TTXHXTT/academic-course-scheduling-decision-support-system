-- Read-only checks of code-review findings against the Neon data (Nov 13, 2026).

-- Q0: one enrollment row per section?
SELECT COUNT(*) AS rows, COUNT(DISTINCT section_id) AS sections
FROM section_enrollment;

-- Q1 (CR-05): term types, incl. Winter
SELECT term_type, COUNT(*) AS terms
FROM academic_term
GROUP BY term_type
ORDER BY terms DESC;

-- Q2 (CR-02): enrollment per term; future terms show 0
SELECT t.term_code, t.term_year, t.term_type,
       COUNT(*) AS sections,
       SUM(e.enrollment_count) AS total_enrolled
FROM course_section cs
JOIN academic_term t USING (term_id)
JOIN section_enrollment e USING (section_id)
GROUP BY t.term_code, t.term_year, t.term_type
ORDER BY t.term_year, t.term_code;

-- Q3 (CR-01): courses whose section count changes across like terms
WITH per_term AS (
  SELECT cs.course_id, t.term_type, t.term_year, COUNT(*) AS sections
  FROM course_section cs
  JOIN academic_term t USING (term_id)
  GROUP BY cs.course_id, t.term_type, t.term_year
)
SELECT course_id, term_type,
       MIN(sections) AS min_sections, MAX(sections) AS max_sections,
       COUNT(*) AS terms_offered
FROM per_term
GROUP BY course_id, term_type
HAVING MAX(sections) > MIN(sections)
ORDER BY MAX(sections) - MIN(sections) DESC
LIMIT 20;

-- Q3b (CR-01, CR-03): CSE 2010 Spring by class type
SELECT t.term_year, cs.class_type,
       COUNT(*) AS sections,
       SUM(e.enrollment_count) AS total_enrolled,
       ROUND(AVG(e.enrollment_count), 1) AS avg_per_section
FROM course_section cs
JOIN academic_term t USING (term_id)
JOIN section_enrollment e USING (section_id)
WHERE cs.course_id = 'CSE 2010' AND t.term_type = 'Spring'
GROUP BY t.term_year, cs.class_type
ORDER BY t.term_year, cs.class_type;

-- Q4 (CR-03): class types, and courses mixing types in one term
SELECT class_type, COUNT(*) AS sections
FROM course_section
GROUP BY class_type
ORDER BY sections DESC;

SELECT COUNT(DISTINCT course_id) AS courses_with_mixed_types
FROM (
  SELECT course_id, term_id
  FROM course_section
  GROUP BY course_id, term_id
  HAVING COUNT(DISTINCT class_type) > 1
) x;
