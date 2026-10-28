# Import all models to ensure they are registered with SQLAlchemy's metadata
from .user import User
from .dataset import Dataset, ImportJob, ValidationIssue
from .course_record import CourseRecord
from .analysis import AnalysisRun, CourseAnalysis
from .recommendation import Recommendation, RecommendationEvidence
from .scenario import Scenario, ScenarioResult
from .audit import AuditEvent

__all__ = [
    "User",
    "Dataset", "ImportJob", "ValidationIssue",
    "CourseRecord",
    "AnalysisRun", "CourseAnalysis",
    "Recommendation", "RecommendationEvidence",
    "Scenario", "ScenarioResult",
    "AuditEvent",
]
