"""
Analysis service: bridges the database and the pure analytics engine.
Implements FR-04, Module E, DR-03.
"""
from __future__ import annotations
import json
from datetime import datetime, timezone
from typing import Optional, List

from sqlalchemy.orm import Session

from app.models.dataset import Dataset
from app.models.course_record import CourseRecord
from app.models.analysis import AnalysisRun, CourseAnalysis
from app.models.user import User
from app.analytics.demand_engine import DemandEngine, AnalysisParameters
from app.analytics.metrics import SectionData
from app.core.config import settings


class AnalysisService:
    def __init__(self, db: Session):
        self.db = db

    def run_analysis(
        self,
        dataset_id: int,
        user: Optional[User] = None,
        name: Optional[str] = None,
        is_baseline: bool = False,
    ) -> AnalysisRun:
        """
        Run demand analysis on a dataset and persist results.
        Uses method version from config for traceability (DR-03).
        """
        params = AnalysisParameters(
            high_utilization_threshold=settings.HIGH_UTILIZATION_THRESHOLD,
            low_utilization_threshold=settings.LOW_UTILIZATION_THRESHOLD,
            full_capacity_threshold=settings.FULL_CAPACITY_THRESHOLD,
            frequently_full_threshold=settings.FREQUENTLY_FULL_THRESHOLD,
            increasing_demand_slope=settings.INCREASING_DEMAND_SLOPE,
            min_terms_for_trend=settings.MIN_TERMS_FOR_TREND,
            method_version=settings.ANALYTICS_METHOD_VERSION,
        )

        run = AnalysisRun(
            name=name or f"Analysis of dataset {dataset_id}",
            dataset_id=dataset_id,
            run_by_id=user.id if user else None,
            started_at=datetime.now(timezone.utc),
            status="running",
            method_version=params.method_version,
            parameters_json=json.dumps({
                "high_utilization_threshold": params.high_utilization_threshold,
                "low_utilization_threshold": params.low_utilization_threshold,
                "full_capacity_threshold": params.full_capacity_threshold,
                "frequently_full_threshold": params.frequently_full_threshold,
                "increasing_demand_slope": params.increasing_demand_slope,
                "min_terms_for_trend": params.min_terms_for_trend,
            }),
            is_baseline=is_baseline,
        )
        self.db.add(run)
        self.db.flush()

        try:
            # Load course records (exclude records with errors)
            db_records: List[CourseRecord] = (
                self.db.query(CourseRecord)
                .filter(
                    CourseRecord.dataset_id == dataset_id,
                    CourseRecord.excluded_from_analysis == False,
                )
                .all()
            )

            if not db_records:
                run.status = "completed"
                run.completed_at = datetime.now(timezone.utc)
                run.courses_analyzed = 0
                self.db.commit()
                return run

            # Convert to SectionData for the pure engine
            sections = [self._record_to_section(r) for r in db_records]

            # Run the pure analytics engine
            engine = DemandEngine(params)
            result = engine.analyze(sections)

            # Persist course analysis results
            for course_id, metrics in result.course_metrics.items():
                ca = CourseAnalysis(
                    analysis_run_id=run.id,
                    course_id=course_id,
                    course_name=metrics.course_name,
                    avg_enrollment=metrics.avg_enrollment,
                    avg_utilization_pct=metrics.avg_utilization_pct,
                    peak_enrollment=metrics.peak_enrollment,
                    min_enrollment=metrics.min_enrollment,
                    total_sections=metrics.total_sections,
                    terms_offered=metrics.terms_offered,
                    terms_list=json.dumps(metrics.terms_list),
                    full_capacity_count=metrics.full_capacity_count,
                    full_capacity_rate=metrics.full_capacity_rate,
                    demand_trend=metrics.demand_trend,
                    demand_trend_score=metrics.demand_trend_score,
                    trend_r_squared=metrics.trend_r_squared,
                    has_unmet_demand_data=metrics.has_unmet_demand_data,
                    avg_unmet_demand=metrics.avg_unmet_demand,
                    total_unmet_demand=metrics.total_unmet_demand,
                    insufficient_data=metrics.insufficient_data,
                    limitations_json=json.dumps(metrics.limitations),
                    evidence_json=json.dumps(metrics.evidence),
                )
                self.db.add(ca)

            run.courses_analyzed = len(result.course_metrics)
            run.status = "completed"
            run.completed_at = datetime.now(timezone.utc)
            self.db.commit()

        except Exception as e:
            run.status = "failed"
            run.error_message = str(e)[:1000]
            run.completed_at = datetime.now(timezone.utc)
            self.db.commit()
            raise

        return run

    def _record_to_section(self, record: CourseRecord) -> SectionData:
        return SectionData(
            course_id=record.course_id,
            term=record.term,
            year=record.year,
            enrollment=record.enrollment,
            capacity=record.capacity,
            attempted_enrollment=record.attempted_enrollment,
            unmet_demand=record.unmet_demand,
            modality=record.modality,
            section_id=record.section_id,
            course_name=record.course_name,
        )
