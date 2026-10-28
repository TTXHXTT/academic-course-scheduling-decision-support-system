"""
Recommendation persistence service.
Implements FR-05, FR-06, Module F.
"""
from __future__ import annotations
import json
from typing import List, Optional

from sqlalchemy.orm import Session

from app.models.analysis import AnalysisRun
from app.models.recommendation import Recommendation, RecommendationEvidence
from app.analytics.demand_engine import DemandEngine, AnalysisParameters
from app.analytics.metrics import SectionData
from app.analytics.rules import RuleResult
from app.models.course_record import CourseRecord
from app.core.config import settings


class RecommendationService:
    def __init__(self, db: Session):
        self.db = db

    def generate_recommendations(self, analysis_run_id: int) -> List[Recommendation]:
        """
        Generate and persist recommendations from a completed analysis run.
        Evidence items link back to specific course records for traceability.
        """
        run: Optional[AnalysisRun] = self.db.get(AnalysisRun, analysis_run_id)
        if not run:
            raise ValueError(f"AnalysisRun {analysis_run_id} not found")

        # Delete existing recommendations for this run before regenerating
        self.db.query(Recommendation).filter(
            Recommendation.analysis_run_id == analysis_run_id
        ).delete()
        self.db.flush()

        params = AnalysisParameters(
            high_utilization_threshold=settings.HIGH_UTILIZATION_THRESHOLD,
            low_utilization_threshold=settings.LOW_UTILIZATION_THRESHOLD,
            full_capacity_threshold=settings.FULL_CAPACITY_THRESHOLD,
            frequently_full_threshold=settings.FREQUENTLY_FULL_THRESHOLD,
            increasing_demand_slope=settings.INCREASING_DEMAND_SLOPE,
            min_terms_for_trend=settings.MIN_TERMS_FOR_TREND,
            method_version=settings.ANALYTICS_METHOD_VERSION,
        )

        # Load records and re-run analytics
        db_records: List[CourseRecord] = (
            self.db.query(CourseRecord)
            .filter(
                CourseRecord.dataset_id == run.dataset_id,
                CourseRecord.excluded_from_analysis == False,
            )
            .all()
        )

        sections = [
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

        engine = DemandEngine(params)
        result = engine.analyze(sections)

        # Build course_id -> records lookup for evidence linking
        records_by_course: dict = {}
        for r in db_records:
            records_by_course.setdefault(r.course_id, []).append(r)

        saved: List[Recommendation] = []
        for rule_result in result.recommendations:
            rec = Recommendation(
                analysis_run_id=analysis_run_id,
                course_id=rule_result.course_id,
                course_name=rule_result.course_name,
                category=rule_result.category,
                category_label=rule_result.category_label,
                priority=rule_result.priority,
                title=rule_result.title,
                explanation=rule_result.explanation,
                rule_applied=rule_result.rule_applied,
                rule_description=rule_result.rule_description,
                limitations=rule_result.limitations,
                suggested_followup=rule_result.suggested_followup,
                key_metric_name=rule_result.key_metric_name,
                key_metric_value=rule_result.key_metric_value,
                key_metric_threshold=rule_result.key_metric_threshold,
                insufficient_evidence=rule_result.insufficient_evidence,
                dataset_id=run.dataset_id,
                analysis_method_version=params.method_version,
            )
            self.db.add(rec)
            self.db.flush()

            # Add evidence items
            for ev in rule_result.evidence_items:
                evidence = RecommendationEvidence(
                    recommendation_id=rec.id,
                    evidence_type=ev.get("type", "general"),
                    term=ev.get("term"),
                    metric_name=ev.get("metric"),
                    metric_value=ev.get("value") if isinstance(ev.get("value"), float) else (
                        float(ev["value"]) if ev.get("value") is not None else None
                    ),
                    description=ev.get("description", ""),
                )
                self.db.add(evidence)
            saved.append(rec)

        self.db.commit()
        return saved
