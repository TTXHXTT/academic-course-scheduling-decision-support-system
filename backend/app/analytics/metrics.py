"""
ACS Analytics Metrics Module
All calculation functions used by the demand engine.

Formulas documented here are prototype assumptions, not approved CSUSB policies.
Thresholds are configurable via app/core/config.py.

SRS References: FR-04, DR-02, NFR-04
Analytics Methodology version: 1.0.0
"""
from __future__ import annotations
from dataclasses import dataclass, field
from typing import List, Optional, Dict, Any, Tuple
import statistics


@dataclass
class SectionData:
    """
    Data for a single course section offering in one term.
    None values indicate missing/unknown data, NOT zero.
    """
    course_id: str
    term: str
    year: Optional[int]
    enrollment: Optional[int]
    capacity: Optional[int]
    attempted_enrollment: Optional[int] = None
    unmet_demand: Optional[int] = None
    modality: Optional[str] = None
    section_id: Optional[str] = None
    course_name: Optional[str] = None


@dataclass
class CourseMetrics:
    """
    Computed metrics for one course across all its sections in the dataset.
    None values indicate the metric could not be computed, not that it is zero.
    """
    course_id: str
    course_name: Optional[str] = None
    total_sections: int = 0
    valid_sections: int = 0  # sections with both enrollment and capacity > 0
    terms_offered: int = 0
    terms_list: List[str] = field(default_factory=list)

    # Enrollment metrics
    avg_enrollment: Optional[float] = None
    peak_enrollment: Optional[int] = None
    min_enrollment: Optional[int] = None
    enrollments_by_term: Dict[str, List[int]] = field(default_factory=dict)  # term -> list of enrollments

    # Capacity utilization (weighted: sum(enroll)/sum(cap)*100)
    # Prototype assumption: weighted aggregate avoids distortion from small sections
    avg_utilization_pct: Optional[float] = None
    utilization_by_term: Dict[str, float] = field(default_factory=dict)  # term -> pct

    # Full capacity analysis
    # full_capacity_threshold (default 0.95 = 95%) - configurable
    full_capacity_count: Optional[int] = None
    full_capacity_rate: Optional[float] = None  # proportion 0.0-1.0

    # Demand trend (linear regression slope, students per term)
    demand_trend: Optional[str] = None  # INCREASING, DECREASING, STABLE, INSUFFICIENT_DATA
    demand_trend_score: Optional[float] = None  # regression slope
    trend_r_squared: Optional[float] = None

    # Unmet demand (only computed when field is present in data)
    has_unmet_demand_data: bool = False
    avg_unmet_demand: Optional[float] = None
    total_unmet_demand: Optional[int] = None

    # Data quality
    insufficient_data: bool = False
    limitations: List[str] = field(default_factory=list)
    evidence: Dict[str, Any] = field(default_factory=dict)


def compute_section_utilization(enrollment: Optional[int], capacity: Optional[int]) -> Optional[float]:
    """
    Capacity Utilization = enrollment / capacity * 100
    Returns None if capacity is missing, zero, or negative.
    Returns None if enrollment is missing.
    Does NOT treat missing values as zero.

    SRS FR-04: 'Only calculate this when capacity is valid and greater than zero.'
    """
    if enrollment is None or capacity is None:
        return None
    if capacity <= 0:
        return None
    return (enrollment / capacity) * 100.0


def compute_weighted_utilization(sections: List[SectionData]) -> Optional[float]:
    """
    Weighted Aggregate Utilization = sum(enrollment) / sum(capacity) * 100
    Only includes sections where both enrollment and capacity are valid (> 0).
    
    SRS FR-04: 'For aggregate utilization, use a clearly documented weighted formula,
    such as total enrollment divided by total capacity, when the included records have
    compatible meanings. Do not simply average percentages.'
    """
    valid_sections = [
        s for s in sections
        if s.enrollment is not None and s.capacity is not None
        and s.capacity > 0 and s.enrollment >= 0
    ]
    if not valid_sections:
        return None
    total_enrollment = sum(s.enrollment for s in valid_sections)
    total_capacity = sum(s.capacity for s in valid_sections)
    if total_capacity == 0:
        return None
    return (total_enrollment / total_capacity) * 100.0


def compute_full_capacity_rate(
    sections: List[SectionData],
    threshold: float = 0.95
) -> Tuple[Optional[int], Optional[float]]:
    """
    Full Capacity Rate = count(enrollment >= capacity * threshold) / count(valid_sections)
    
    threshold default 0.95 means 95% full counts as 'at capacity'.
    Prototype assumption: this threshold is configurable and documented.
    
    Returns (count, rate) where rate is 0.0-1.0, or (None, None) if no valid sections.
    """
    valid_sections = [
        s for s in sections
        if s.enrollment is not None and s.capacity is not None and s.capacity > 0
    ]
    if not valid_sections:
        return None, None
    full = sum(
        1 for s in valid_sections
        if s.enrollment >= s.capacity * threshold
    )
    return full, full / len(valid_sections)


def compute_demand_trend(
    sections: List[SectionData],
    min_terms: int = 2,
    increasing_slope_threshold: float = 2.0,
) -> Tuple[Optional[str], Optional[float], Optional[float]]:
    """
    Demand Trend: linear regression of average enrollment per comparable term.
    
    Method:
    1. Group sections by term (comparable periods only)
    2. Compute average enrollment per term
    3. Assign a term index (sorted chronologically)
    4. Run simple linear regression
    5. Classify by slope vs threshold

    Returns (trend_label, slope, r_squared)
    trend_label: INCREASING, DECREASING, STABLE, INSUFFICIENT_DATA

    SRS FR-04: 'Use a documented method based on comparable historical periods.
    Handle missing periods, new courses, and irregular offering schedules explicitly.'
    
    INSUFFICIENT_DATA returned when fewer than min_terms distinct terms have data.
    """
    # Group by term, average enrollment
    term_enrollments: Dict[str, List[int]] = {}
    for s in sections:
        if s.enrollment is not None and s.enrollment >= 0:
            term_enrollments.setdefault(s.term, []).append(s.enrollment)

    if len(term_enrollments) < min_terms:
        return "INSUFFICIENT_DATA", None, None

    # Sort terms - use sort key that puts years first
    sorted_terms = sorted(term_enrollments.keys(), key=_term_sort_key)
    term_avgs = [(i, statistics.mean(term_enrollments[t])) for i, t in enumerate(sorted_terms)]

    if len(term_avgs) < 2:
        return "INSUFFICIENT_DATA", None, None

    xs = [x for x, _ in term_avgs]
    ys = [y for _, y in term_avgs]
    slope, intercept, r_squared = _linear_regression(xs, ys)

    if slope >= increasing_slope_threshold:
        trend = "INCREASING"
    elif slope <= -increasing_slope_threshold:
        trend = "DECREASING"
    else:
        trend = "STABLE"

    return trend, slope, r_squared


def _term_sort_key(term: str) -> tuple:
    """
    Sort academic terms chronologically.
    Handles formats like 'Fall 2023', 'Spring 2024', 'Summer 2023'.
    """
    semester_order = {"winter": 0, "spring": 1, "summer": 2, "fall": 3}
    parts = term.lower().split()
    year = 0
    sem_idx = 0
    for part in parts:
        if part.isdigit() and len(part) == 4:
            year = int(part)
        elif part in semester_order:
            sem_idx = semester_order[part]
    return (year, sem_idx)


def _linear_regression(xs: List[float], ys: List[float]) -> Tuple[float, float, float]:
    """
    Simple ordinary least squares linear regression.
    Returns (slope, intercept, r_squared).
    Uses only Python stdlib - no numpy required.
    """
    n = len(xs)
    if n < 2:
        return 0.0, 0.0, 0.0

    mean_x = sum(xs) / n
    mean_y = sum(ys) / n

    ss_xx = sum((x - mean_x) ** 2 for x in xs)
    ss_xy = sum((x - mean_x) * (y - mean_y) for x, y in zip(xs, ys))
    ss_yy = sum((y - mean_y) ** 2 for y in ys)

    if ss_xx == 0:
        return 0.0, mean_y, 0.0

    slope = ss_xy / ss_xx
    intercept = mean_y - slope * mean_x
    r_squared = (ss_xy ** 2) / (ss_xx * ss_yy) if ss_yy != 0 else 1.0

    return slope, intercept, r_squared


def compute_unmet_demand(sections: List[SectionData]) -> Tuple[bool, Optional[float], Optional[int]]:
    """
    Compute unmet demand from explicit unmet_demand or attempted_enrollment fields.
    
    SRS FR-04: 'Do not infer unmet demand from enrollment alone when no
    attempted-enrollment or unmet-demand field exists.'
    
    Returns (has_data, avg_unmet_demand, total_unmet_demand)
    """
    # Try direct unmet_demand field first
    direct = [s.unmet_demand for s in sections if s.unmet_demand is not None]
    if direct:
        return True, sum(direct) / len(direct), sum(direct)

    # Try computed from attempted_enrollment - enrollment
    computed = []
    for s in sections:
        if s.attempted_enrollment is not None and s.enrollment is not None:
            computed.append(max(0, s.attempted_enrollment - s.enrollment))
    if computed:
        return True, sum(computed) / len(computed), sum(computed)

    # Do NOT infer from enrollment alone
    return False, None, None


def compute_course_metrics(
    course_id: str,
    sections: List[SectionData],
    high_util_threshold: float = 85.0,
    low_util_threshold: float = 50.0,
    full_cap_threshold: float = 0.95,
    frequently_full_threshold: float = 0.50,
    increasing_slope: float = 2.0,
    min_terms_for_trend: int = 2,
) -> CourseMetrics:
    """
    Compute all metrics for a course. Master entry point.
    All thresholds are configurable and documented as prototype assumptions.
    """
    metrics = CourseMetrics(
        course_id=course_id,
        course_name=next((s.course_name for s in sections if s.course_name), None),
        total_sections=len(sections),
    )

    limitations = []

    # Valid sections: both enrollment and capacity are non-None and capacity > 0
    valid_sections = [
        s for s in sections
        if s.enrollment is not None and s.capacity is not None and s.capacity > 0
    ]
    metrics.valid_sections = len(valid_sections)

    # Terms offered
    all_terms = list(set(s.term for s in sections))
    all_terms.sort(key=_term_sort_key)
    metrics.terms_offered = len(all_terms)
    metrics.terms_list = all_terms

    # Enrollment stats
    enrollments = [s.enrollment for s in sections if s.enrollment is not None]
    if enrollments:
        metrics.avg_enrollment = sum(enrollments) / len(enrollments)
        metrics.peak_enrollment = max(enrollments)
        metrics.min_enrollment = min(enrollments)
    else:
        limitations.append("No valid enrollment data available.")

    # Enrollments by term (for charts)
    for s in sections:
        if s.enrollment is not None:
            metrics.enrollments_by_term.setdefault(s.term, []).append(s.enrollment)

    # Utilization
    metrics.avg_utilization_pct = compute_weighted_utilization(sections)
    if metrics.avg_utilization_pct is None:
        limitations.append("Could not compute capacity utilization: missing or invalid capacity/enrollment data.")

    # Utilization by term
    for s in sections:
        util = compute_section_utilization(s.enrollment, s.capacity)
        if util is not None:
            metrics.utilization_by_term.setdefault(s.term, []).append(util)
    # Average per term
    metrics.utilization_by_term = {
        t: sum(v) / len(v) for t, v in metrics.utilization_by_term.items()
    }

    # Full capacity rate
    fc_count, fc_rate = compute_full_capacity_rate(valid_sections, threshold=full_cap_threshold)
    metrics.full_capacity_count = fc_count
    metrics.full_capacity_rate = fc_rate
    if fc_rate is None:
        limitations.append("Could not compute full-capacity rate: insufficient valid section data.")

    # Demand trend
    trend, slope, r2 = compute_demand_trend(
        sections,
        min_terms=min_terms_for_trend,
        increasing_slope_threshold=increasing_slope,
    )
    metrics.demand_trend = trend
    metrics.demand_trend_score = slope
    metrics.trend_r_squared = r2
    if trend == "INSUFFICIENT_DATA":
        limitations.append(f"Demand trend could not be computed: fewer than {min_terms_for_trend} terms with enrollment data.")

    # Unmet demand
    has_ud, avg_ud, total_ud = compute_unmet_demand(sections)
    metrics.has_unmet_demand_data = has_ud
    metrics.avg_unmet_demand = avg_ud
    metrics.total_unmet_demand = total_ud
    if not has_ud:
        limitations.append("Unmet demand not available: no attempted_enrollment or unmet_demand field in data.")

    # Data quality flags
    if metrics.valid_sections == 0:
        metrics.insufficient_data = True
        limitations.append("No sections with both valid enrollment and capacity data.")
    elif metrics.valid_sections < 2:
        limitations.append("Only one valid section; some metrics may be unreliable.")

    metrics.limitations = limitations

    # Build evidence dict for traceability
    metrics.evidence = {
        "terms_analyzed": all_terms,
        "sections_analyzed": metrics.total_sections,
        "valid_sections": metrics.valid_sections,
        "enrollment_by_term": {t: v for t, v in metrics.enrollments_by_term.items()},
    }

    return metrics
