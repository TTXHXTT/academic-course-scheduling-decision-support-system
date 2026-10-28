"""
What-if scenario execution service.
Implements FR-07, FR-08, Module G.

Scenarios NEVER modify original historical data (AC-14).
All results are clearly labeled as simulated.
"""
from __future__ import annotations
import json
from datetime import datetime, timezone
from typing import List, Dict, Any, Optional

from sqlalchemy.orm import Session

from app.models.scenario import Scenario, ScenarioResult
from app.models.analysis import AnalysisRun, CourseAnalysis
from app.models.course_record import CourseRecord
from app.models.user import User
from app.analytics.demand_engine import DemandEngine, AnalysisParameters
from app.analytics.metrics import SectionData
from app.core.config import settings


class ScenarioService:
    def __init__(self, db: Session):
        self.db = db

    def create_and_run_scenario(
        self,
        name: str,
        description: Optional[str],
        baseline_analysis_id: int,
        scenario_type: str,
        parameters: Dict[str, Any],
        user: Optional[User] = None,
    ) -> Scenario:
        """
        Create a what-if scenario and compute its results.
        The original dataset and baseline results are never modified.
        """
        baseline_run: Optional[AnalysisRun] = self.db.get(AnalysisRun, baseline_analysis_id)
        if not baseline_run:
            raise ValueError(f"Baseline analysis {baseline_analysis_id} not found")

        scenario = Scenario(
            name=name,
            description=description,
            baseline_analysis_id=baseline_analysis_id,
            dataset_id=baseline_run.dataset_id,
            created_by_id=user.id if user else None,
            created_at=datetime.now(timezone.utc),
            scenario_type=scenario_type,
            parameters_json=json.dumps(parameters),
            status="pending",
            method_version=settings.ANALYTICS_METHOD_VERSION,
        )
        self.db.add(scenario)
        self.db.flush()

        try:
            results = self._execute_scenario(scenario, baseline_run, parameters)
            for result in results:
                self.db.add(result)
            scenario.status = "completed"
            self.db.commit()
        except Exception as e:
            scenario.status = "failed"
            self.db.commit()
            raise

        self.db.refresh(scenario)
        return scenario

    def _execute_scenario(
        self,
        scenario: Scenario,
        baseline_run: AnalysisRun,
        parameters: Dict[str, Any],
    ) -> List[ScenarioResult]:
        """Apply scenario modifications and compute comparison results."""
        # Load original records (never modified)
        db_records: List[CourseRecord] = (
            self.db.query(CourseRecord)
            .filter(
                CourseRecord.dataset_id == baseline_run.dataset_id,
                CourseRecord.excluded_from_analysis == False,
            )
            .all()
        )

        original_sections = [
            SectionData(
                course_id=r.course_id,
                term=r.term,
                year=r.year,
                enrollment=r.enrollment,
                capacity=r.capacity,
                attempted_enrollment=r.attempted_enrollment,
                unmet_demand=r.unmet_demand,
                modality=r.modality,
                section_id=r.section_id,
                course_name=r.course_name,
            )
            for r in db_records
        ]

        # Build modified sections based on scenario type
        modified_sections = self._apply_scenario(
            original_sections, scenario.scenario_type, parameters
        )

        # Run analytics on both
        params = AnalysisParameters(
            high_utilization_threshold=settings.HIGH_UTILIZATION_THRESHOLD,
            low_utilization_threshold=settings.LOW_UTILIZATION_THRESHOLD,
            full_capacity_threshold=settings.FULL_CAPACITY_THRESHOLD,
            frequently_full_threshold=settings.FREQUENTLY_FULL_THRESHOLD,
            increasing_demand_slope=settings.INCREASING_DEMAND_SLOPE,
            min_terms_for_trend=settings.MIN_TERMS_FOR_TREND,
        )
        engine = DemandEngine(params)
        baseline_result = engine.analyze(original_sections)
        scenario_result = engine.analyze(modified_sections)

        # Build per-course comparison results
        results: List[ScenarioResult] = []
        affected_course = parameters.get("course_id")
        all_courses = set(baseline_result.course_metrics) | set(scenario_result.course_metrics)

        for course_id in all_courses:
            bm = baseline_result.course_metrics.get(course_id)
            sm = scenario_result.course_metrics.get(course_id)

            b_util = bm.avg_utilization_pct if bm else None
            s_util = sm.avg_utilization_pct if sm else None
            b_cap = int(bm.avg_capacity) if bm and bm.avg_capacity else None
            s_cap = int(sm.avg_capacity) if sm and sm.avg_capacity else None

            changes: Dict[str, Any] = {"has_changes": course_id == affected_course}
            if b_util is not None and s_util is not None and abs(b_util - s_util) > 0.01:
                changes["utilization_pct"] = {"baseline": round(b_util, 2), "scenario": round(s_util, 2), "delta": round(s_util - b_util, 2)}
                changes["has_changes"] = True
            if bm and sm and bm.total_sections != sm.total_sections:
                changes["total_sections"] = {"baseline": bm.total_sections, "scenario": sm.total_sections, "delta": sm.total_sections - bm.total_sections}
                changes["has_changes"] = True
            if bm and sm and bm.demand_trend != sm.demand_trend:
                changes["demand_trend"] = {"baseline": bm.demand_trend, "scenario": sm.demand_trend}

            warnings: List[str] = ["SIMULATED RESULTS: These are not historical observations."]
            if scenario.scenario_type == "add_section" and course_id == affected_course:
                warnings.append("Added section is hypothetical. Faculty and room availability not checked.")
            elif scenario.scenario_type == "demand_increase" and course_id == affected_course:
                warnings.append("Demand increase is hypothetical. Actual demand depends on many factors.")

            result = ScenarioResult(
                scenario_id=scenario.id,
                course_id=course_id,
                course_name=bm.course_name if bm else (sm.course_name if sm else None),
                baseline_utilization_pct=b_util,
                scenario_utilization_pct=s_util,
                baseline_capacity=b_cap,
                scenario_capacity=s_cap,
                baseline_sections=bm.total_sections if bm else None,
                scenario_sections=sm.total_sections if sm else None,
                baseline_demand_trend=bm.demand_trend if bm else None,
                scenario_demand_trend=sm.demand_trend if sm else None,
                baseline_value_json=json.dumps({
                    "avg_enrollment": bm.avg_enrollment,
                    "avg_utilization_pct": b_util,
                    "total_sections": bm.total_sections,
                    "demand_trend": bm.demand_trend,
                    "full_capacity_rate": bm.full_capacity_rate,
                    "limitations": bm.limitations,
                }) if bm else None,
                scenario_value_json=json.dumps({
                    "avg_enrollment": sm.avg_enrollment,
                    "avg_utilization_pct": s_util,
                    "total_sections": sm.total_sections,
                    "demand_trend": sm.demand_trend,
                    "full_capacity_rate": sm.full_capacity_rate,
                    "is_simulated": True,
                }) if sm else None,
                changes_json=json.dumps(changes),
                warnings_json=json.dumps(warnings),
                assumptions_json=json.dumps({
                    "method_version": settings.ANALYTICS_METHOD_VERSION,
                    "scenario_type": scenario.scenario_type,
                    "parameters": parameters,
                    "note": "Scenario results are simulated. They do not represent historical data.",
                }),
                is_affected=course_id == affected_course,
                calculated_at=datetime.now(timezone.utc),
            )
            results.append(result)

        return results

    def _apply_scenario(
        self,
        sections: List[SectionData],
        scenario_type: str,
        parameters: Dict[str, Any],
    ) -> List[SectionData]:
        """
        Apply scenario modifications. Never modifies original sections list.
        Returns a new list with hypothetical changes applied.
        """
        import copy
        modified = [copy.copy(s) for s in sections]  # shallow copy - never modifies originals
        course_id = parameters.get("course_id")

        if scenario_type == "add_section":
            # Add a hypothetical section with specified or default capacity
            new_capacity = parameters.get("capacity", 30)
            assumed_enrollment = parameters.get("assumed_enrollment", 0)
            term = parameters.get("term", "Hypothetical Term")
            course_name = next((s.course_name for s in sections if s.course_id == course_id), None)
            new_section = SectionData(
                course_id=course_id,
                term=term,
                year=None,
                enrollment=assumed_enrollment,
                capacity=new_capacity,
                course_name=course_name,
            )
            modified.append(new_section)

        elif scenario_type == "change_capacity":
            new_capacity = parameters.get("new_capacity")
            if new_capacity and new_capacity > 0:
                for s in modified:
                    if s.course_id == course_id:
                        s.capacity = new_capacity

        elif scenario_type == "change_modality":
            new_modality = parameters.get("new_modality", "Online")
            for s in modified:
                if s.course_id == course_id:
                    s.modality = new_modality

        elif scenario_type == "demand_increase":
            increase_pct = parameters.get("increase_pct", 10)
            factor = 1 + (increase_pct / 100.0)
            for s in modified:
                if s.course_id == course_id and s.enrollment is not None:
                    s.enrollment = int(s.enrollment * factor)
                    if s.capacity and s.enrollment > s.capacity:
                        pass  # enrollment > capacity is valid - shows over-demand

        elif scenario_type == "limit_sections":
            max_sections = parameters.get("max_sections", 1)
            count = 0
            filtered = []
            for s in modified:
                if s.course_id == course_id:
                    if count < max_sections:
                        filtered.append(s)
                        count += 1
                else:
                    filtered.append(s)
            modified = filtered

        return modified
