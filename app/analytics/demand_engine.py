"""
ACS Demand Analysis Engine

Pure analytics module - no HTTP framework, no database dependencies.
Completely independently testable.

SRS Reference: FR-04, Module E
Method Version: 1.0.0

All thresholds are prototype assumptions, documented and configurable.
Not CSUSB-approved policies.
"""
from __future__ import annotations
from dataclasses import dataclass, field
from typing import List, Dict, Optional, Any

from .metrics import (
    SectionData,
    CourseMetrics,
    compute_course_metrics,
)
from .rules import RecommendationRules, RuleResult


@dataclass
class AnalysisParameters:
    """
    Configuration for one analysis run.
    All values are prototype assumptions; none are CSUSB policies.
    These are displayed to users alongside results.
    """
    high_utilization_threshold: float = 85.0
    low_utilization_threshold: float = 50.0
    full_capacity_threshold: float = 0.95
    frequently_full_threshold: float = 0.50
    increasing_demand_slope: float = 2.0
    min_terms_for_trend: int = 2
    method_version: str = "1.0.0"


@dataclass
class DemandAnalysisResult:
    """Complete result of a demand analysis run."""
    parameters: AnalysisParameters
    course_metrics: Dict[str, CourseMetrics]  # course_id -> metrics
    recommendations: List[RuleResult]
    total_courses: int = 0
    total_sections: int = 0
    courses_with_insufficient_data: int = 0
    warnings: List[str] = field(default_factory=list)


class DemandEngine:
    """
    Main analytics engine for ACS.
    
    Usage:
        engine = DemandEngine(parameters)
        sections = [SectionData(...)]
        result = engine.analyze(sections)
    
    The engine is deterministic: identical inputs produce identical outputs.
    The engine does not access the database, filesystem, or network.
    """

    def __init__(self, parameters: Optional[AnalysisParameters] = None):
        self.parameters = parameters or AnalysisParameters()
        self.rules = RecommendationRules(self.parameters)

    def analyze(self, sections: List[SectionData]) -> DemandAnalysisResult:
        """
        Run demand analysis on a list of section data records.
        
        Steps:
        1. Group sections by course_id
        2. Compute metrics for each course
        3. Apply recommendation rules
        4. Return complete result
        
        Original section data is not modified.
        """
        if not sections:
            return DemandAnalysisResult(
                parameters=self.parameters,
                course_metrics={},
                recommendations=[],
                warnings=["No section data provided for analysis."]
            )

        # Group by course
        courses: Dict[str, List[SectionData]] = {}
        for section in sections:
            courses.setdefault(section.course_id, []).append(section)

        # Compute metrics per course
        course_metrics: Dict[str, CourseMetrics] = {}
        for course_id, course_sections in courses.items():
            metrics = compute_course_metrics(
                course_id=course_id,
                sections=course_sections,
                high_util_threshold=self.parameters.high_utilization_threshold,
                low_util_threshold=self.parameters.low_utilization_threshold,
                full_cap_threshold=self.parameters.full_capacity_threshold,
                frequently_full_threshold=self.parameters.frequently_full_threshold,
                increasing_slope=self.parameters.increasing_demand_slope,
                min_terms_for_trend=self.parameters.min_terms_for_trend,
            )
            course_metrics[course_id] = metrics

        # Generate recommendations
        all_recommendations: List[RuleResult] = []
        for course_id, metrics in course_metrics.items():
            recs = self.rules.evaluate(metrics)
            all_recommendations.extend(recs)

        # Sort by priority
        priority_order = {"high": 0, "medium": 1, "low": 2, "informational": 3}
        all_recommendations.sort(key=lambda r: priority_order.get(r.priority, 99))

        insufficient = sum(1 for m in course_metrics.values() if m.insufficient_data)

        return DemandAnalysisResult(
            parameters=self.parameters,
            course_metrics=course_metrics,
            recommendations=all_recommendations,
            total_courses=len(course_metrics),
            total_sections=len(sections),
            courses_with_insufficient_data=insufficient,
        )

    def compare_scenario(
        self,
        baseline_result: DemandAnalysisResult,
        modified_sections: List[SectionData],
        scenario_type: str,
        scenario_params: Dict[str, Any],
    ) -> Dict[str, Any]:
        """
        Compare a what-if scenario against a baseline analysis.
        
        The baseline result is never modified.
        Clearly labels simulated results vs historical observations.
        
        SRS FR-07, FR-08: scenario comparison
        AC-14: does not overwrite original data
        """
        scenario_result = self.analyze(modified_sections)

        comparison = {
            "scenario_type": scenario_type,
            "scenario_params": scenario_params,
            "method_version": self.parameters.method_version,
            "is_simulated": True,  # Always label as simulated
            "WARNING": "Scenario results are simulated. They are not historical observations.",
            "course_comparisons": {},
        }

        # Build per-course comparison
        all_course_ids = set(baseline_result.course_metrics.keys()) | set(scenario_result.course_metrics.keys())
        for course_id in all_course_ids:
            baseline_metrics = baseline_result.course_metrics.get(course_id)
            scenario_metrics = scenario_result.course_metrics.get(course_id)

            baseline_dict = _metrics_to_dict(baseline_metrics) if baseline_metrics else {}
            scenario_dict = _metrics_to_dict(scenario_metrics) if scenario_metrics else {}

            changes = _compute_changes(baseline_dict, scenario_dict)
            is_affected = course_id in [str(v) for v in scenario_params.values()] or changes.get("has_changes", False)

            comparison["course_comparisons"][course_id] = {
                "course_id": course_id,
                "is_affected": is_affected,
                "baseline": baseline_dict,
                "scenario": scenario_dict,
                "changes": changes,
                "is_simulated": True,
            }

        return comparison


def _metrics_to_dict(metrics: CourseMetrics) -> Dict[str, Any]:
    """Convert CourseMetrics to a serializable dict for comparison."""
    return {
        "course_id": metrics.course_id,
        "course_name": metrics.course_name,
        "avg_enrollment": metrics.avg_enrollment,
        "avg_utilization_pct": metrics.avg_utilization_pct,
        "peak_enrollment": metrics.peak_enrollment,
        "total_sections": metrics.total_sections,
        "terms_offered": metrics.terms_offered,
        "full_capacity_rate": metrics.full_capacity_rate,
        "demand_trend": metrics.demand_trend,
        "demand_trend_score": metrics.demand_trend_score,
        "has_unmet_demand_data": metrics.has_unmet_demand_data,
        "avg_unmet_demand": metrics.avg_unmet_demand,
        "insufficient_data": metrics.insufficient_data,
        "limitations": metrics.limitations,
    }


def _compute_changes(baseline: Dict, scenario: Dict) -> Dict[str, Any]:
    """Identify what changed between baseline and scenario."""
    numeric_keys = [
        "avg_enrollment", "avg_utilization_pct", "peak_enrollment",
        "total_sections", "full_capacity_rate", "demand_trend_score",
        "avg_unmet_demand",
    ]
    string_keys = ["demand_trend"]
    changes: Dict[str, Any] = {"has_changes": False}

    for key in numeric_keys:
        b_val = baseline.get(key)
        s_val = scenario.get(key)
        if b_val is not None and s_val is not None:
            delta = s_val - b_val
            if abs(delta) > 0.001:
                changes[key] = {"baseline": b_val, "scenario": s_val, "delta": delta}
                changes["has_changes"] = True

    for key in string_keys:
        b_val = baseline.get(key)
        s_val = scenario.get(key)
        if b_val != s_val:
            changes[key] = {"baseline": b_val, "scenario": s_val}
            if b_val is not None and s_val is not None:
                changes["has_changes"] = True

    return changes
