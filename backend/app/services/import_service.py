"""
Data import and validation service.
Implements FR-01 (import), DR-01 (fields), DR-02 (validation), Module B, Module C.

Validation codes are stable and documented.
Invalid records are never silently discarded; every issue is recorded.
"""
from __future__ import annotations
import csv
import io
import json
from datetime import datetime, timezone
from typing import List, Dict, Any, Optional, Tuple

from sqlalchemy.orm import Session

from app.models.dataset import Dataset, DatasetStatus, ImportJob, ValidationIssue, IssueType, IssueSeverity
from app.models.course_record import CourseRecord
from app.models.user import User


# Required columns (DR-01 mandatory fields)
REQUIRED_COLUMNS = {"course_id", "term", "enrollment", "capacity"}

# All recognized columns (DR-01)
KNOWN_COLUMNS = {
    "course_id", "course_name", "section_id", "term", "year", "semester",
    "days", "times", "modality", "campus", "enrollment", "capacity",
    "attempted_enrollment", "unmet_demand", "student_demand", "major", "student_level"
}

# Valid modality values (case-insensitive matching applied)
VALID_MODALITIES = {"in-person", "online", "hybrid", "remote", "face-to-face", "blended"}

# Valid semester values
VALID_SEMESTERS = {"fall", "spring", "summer", "winter"}

# Valid student levels
VALID_STUDENT_LEVELS = {"freshman", "sophomore", "junior", "senior", "graduate", "postbaccalaureate"}


class ImportService:
    def __init__(self, db: Session):
        self.db = db

    def import_csv(
        self,
        file_content: bytes,
        dataset_name: str,
        source_filename: str,
        user: Optional[User] = None,
        is_synthetic: bool = False,
        description: Optional[str] = None,
    ) -> Tuple[Dataset, ImportJob]:
        """
        Import a CSV file of historical academic records.
        Returns (Dataset, ImportJob) with full validation results.
        Never silently discards records (DR-02).
        """
        # Create dataset record
        dataset = Dataset(
            name=dataset_name,
            description=description,
            source_filename=source_filename,
            imported_by_id=user.id if user else None,
            imported_at=datetime.now(timezone.utc),
            status=DatasetStatus.pending,
            is_synthetic=is_synthetic,
        )
        self.db.add(dataset)
        self.db.flush()

        # Create import job
        job = ImportJob(
            dataset_id=dataset.id,
            started_at=datetime.now(timezone.utc),
            status="running",
        )
        self.db.add(job)
        self.db.flush()

        try:
            content_str = self._decode_csv(file_content, job)
            if content_str is None:
                self.db.commit()
                return dataset, job

            records, issues = self._parse_and_validate_csv(content_str, job, dataset)

            # Persist issues
            for issue in issues:
                self.db.add(issue)

            # Persist valid records
            for record in records:
                self.db.add(record)

            # Update counts
            total = job.total_rows
            error_rows = sum(1 for i in issues if i.severity == IssueSeverity.error)
            warning_rows = sum(1 for i in issues if i.severity == IssueSeverity.warning)
            valid = len(records)

            job.valid_rows = valid
            job.error_rows = len(set(i.row_number for i in issues if i.severity == IssueSeverity.error and i.row_number))
            job.warning_rows = len(set(i.row_number for i in issues if i.severity == IssueSeverity.warning and i.row_number))
            job.completed_at = datetime.now(timezone.utc)
            job.status = "completed"

            dataset.row_count = total
            dataset.valid_row_count = valid

            if job.error_rows == 0:
                dataset.status = DatasetStatus.valid if job.warning_rows == 0 else DatasetStatus.partial
            elif valid > 0:
                dataset.status = DatasetStatus.partial
            else:
                dataset.status = DatasetStatus.failed

            self.db.commit()

        except Exception as e:
            job.status = "failed"
            job.error_message = str(e)[:1000]
            job.completed_at = datetime.now(timezone.utc)
            dataset.status = DatasetStatus.failed
            self.db.commit()
            raise

        return dataset, job

    def _decode_csv(self, content: bytes, job: ImportJob) -> Optional[str]:
        """Attempt UTF-8 then latin-1 decoding."""
        for encoding in ["utf-8-sig", "utf-8", "latin-1"]:
            try:
                return content.decode(encoding)
            except (UnicodeDecodeError, LookupError):
                continue
        job.status = "failed"
        job.error_message = "Could not decode file: unsupported encoding."
        return None

    def _parse_and_validate_csv(
        self,
        content: str,
        job: ImportJob,
        dataset: Dataset,
    ) -> Tuple[List[CourseRecord], List[ValidationIssue]]:
        """Parse CSV rows and validate each record."""
        records: List[CourseRecord] = []
        issues: List[ValidationIssue] = []

        reader = csv.DictReader(io.StringIO(content))
        if not reader.fieldnames:
            issues.append(self._make_issue(
                job, None, None,
                IssueType.missing_required, "VAL-000",
                "CSV file is empty or has no header row.",
                IssueSeverity.error, None, False
            ))
            job.total_rows = 0
            return records, issues

        # Normalize column names
        fieldnames = [f.strip().lower() for f in reader.fieldnames]
        missing_required = REQUIRED_COLUMNS - set(fieldnames)
        if missing_required:
            issues.append(self._make_issue(
                job, None, None,
                IssueType.missing_required, "VAL-001",
                f"Missing required columns: {sorted(missing_required)}. Import cannot proceed.",
                IssueSeverity.error, None, False
            ))
            job.total_rows = 0
            return records, issues

        # Track seen records for duplicate detection
        seen: set = set()
        row_number = 1

        for row in reader:
            row_number += 1
            # Normalize keys
            normalized = {k.strip().lower(): (v.strip() if v else "") for k, v in row.items()}
            raw_json = json.dumps(dict(zip(reader.fieldnames, row.values())))

            row_issues: List[ValidationIssue] = []
            has_error = False

            # --- Validate required fields ---
            course_id = normalized.get("course_id", "")
            if not course_id:
                row_issues.append(self._make_issue(
                    job, row_number, "course_id",
                    IssueType.missing_required, "VAL-002",
                    "course_id is required and was blank.",
                    IssueSeverity.error, "", False
                ))
                has_error = True

            term = normalized.get("term", "")
            if not term:
                row_issues.append(self._make_issue(
                    job, row_number, "term",
                    IssueType.missing_required, "VAL-003",
                    "term is required and was blank.",
                    IssueSeverity.error, "", False
                ))
                has_error = True

            # --- Validate numeric fields ---
            enrollment = self._parse_int(normalized.get("enrollment"), "enrollment", row_number, job, row_issues)
            capacity = self._parse_int(normalized.get("capacity"), "capacity", row_number, job, row_issues)

            if enrollment is None:
                has_error = True
            elif enrollment < 0:
                row_issues.append(self._make_issue(
                    job, row_number, "enrollment",
                    IssueType.invalid_range, "VAL-004",
                    f"enrollment cannot be negative (got {enrollment}).",
                    IssueSeverity.error, str(enrollment), False
                ))
                has_error = True

            if capacity is None:
                has_error = True  
            elif capacity <= 0:
                row_issues.append(self._make_issue(
                    job, row_number, "capacity",
                    IssueType.invalid_range, "VAL-005",
                    f"capacity must be greater than zero (got {capacity}). This record will be excluded from utilization analysis.",
                    IssueSeverity.warning if capacity == 0 else IssueSeverity.error,
                    str(capacity), capacity == 0
                ))
                if capacity < 0:
                    has_error = True

            # enrollment > capacity: warning, record included
            if enrollment is not None and capacity is not None and capacity > 0 and enrollment > capacity:
                row_issues.append(self._make_issue(
                    job, row_number, "enrollment",
                    IssueType.enrollment_exceeds_capacity, "VAL-006",
                    f"enrollment ({enrollment}) exceeds capacity ({capacity}). Record retained with warning.",
                    IssueSeverity.warning, str(enrollment), True
                ))

            # Optional numeric fields
            attempted_enrollment = self._parse_int_optional(normalized.get("attempted_enrollment"), "attempted_enrollment", row_number, job, row_issues)
            unmet_demand = self._parse_int_optional(normalized.get("unmet_demand"), "unmet_demand", row_number, job, row_issues)
            student_demand = self._parse_int_optional(normalized.get("student_demand"), "student_demand", row_number, job, row_issues)
            year = self._parse_int_optional(normalized.get("year"), "year", row_number, job, row_issues)

            # --- Validate modality ---
            modality = normalized.get("modality") or None
            if modality and modality.lower() not in VALID_MODALITIES:
                row_issues.append(self._make_issue(
                    job, row_number, "modality",
                    IssueType.inconsistent_modality, "VAL-007",
                    f"Unrecognized modality value '{modality}'. Expected: {sorted(VALID_MODALITIES)}. Record retained with warning.",
                    IssueSeverity.warning, modality, True
                ))

            # --- Duplicate detection ---
            dup_key = (course_id, term, normalized.get("section_id", ""))
            if dup_key in seen and course_id:
                row_issues.append(self._make_issue(
                    job, row_number, None,
                    IssueType.duplicate_record, "VAL-008",
                    f"Duplicate record detected: course_id='{course_id}', term='{term}', section_id='{normalized.get('section_id', '')}'. Record retained with warning.",
                    IssueSeverity.warning, None, True
                ))
            elif course_id and term:
                seen.add(dup_key)

            issues.extend(row_issues)

            if has_error:
                # Still record a null/partial record as rejected (not silently dropped)
                continue

            has_warnings = any(i.severity == IssueSeverity.warning for i in row_issues)

            record = CourseRecord(
                dataset_id=dataset.id,
                import_job_id=job.id,
                course_id=course_id,
                course_name=normalized.get("course_name") or None,
                section_id=normalized.get("section_id") or None,
                term=term,
                year=year,
                semester=normalized.get("semester") or None,
                days=normalized.get("days") or None,
                times=normalized.get("times") or None,
                modality=modality,
                campus=normalized.get("campus") or None,
                enrollment=enrollment,
                capacity=capacity,
                attempted_enrollment=attempted_enrollment,
                unmet_demand=unmet_demand,
                student_demand=student_demand,
                major=normalized.get("major") or None,
                student_level=normalized.get("student_level") or None,
                has_warnings=has_warnings,
                excluded_from_analysis=False,
                raw_row_json=raw_json,
            )
            records.append(record)

        job.total_rows = row_number - 1
        return records, issues

    def _parse_int(self, value: str, field: str, row_number: int, job: ImportJob, issues: list) -> Optional[int]:
        """Parse a required integer field. Returns None and adds error issue if invalid."""
        if not value:
            issues.append(self._make_issue(
                job, row_number, field,
                IssueType.missing_required, "VAL-009",
                f"{field} is required but was blank.",
                IssueSeverity.error, value, False
            ))
            return None
        try:
            return int(float(value))
        except (ValueError, TypeError):
            issues.append(self._make_issue(
                job, row_number, field,
                IssueType.invalid_type, "VAL-010",
                f"{field} must be an integer (got '{value}').",
                IssueSeverity.error, value, False
            ))
            return None

    def _parse_int_optional(self, value: str, field: str, row_number: int, job: ImportJob, issues: list) -> Optional[int]:
        """Parse an optional integer field. Returns None if blank (not zero)."""
        if not value:
            return None  # Missing optional field - NOT treated as zero
        try:
            result = int(float(value))
            if result < 0:
                issues.append(self._make_issue(
                    job, row_number, field,
                    IssueType.invalid_range, "VAL-011",
                    f"{field} cannot be negative (got {result}). Field treated as missing.",
                    IssueSeverity.warning, value, True
                ))
                return None
            return result
        except (ValueError, TypeError):
            issues.append(self._make_issue(
                job, row_number, field,
                IssueType.invalid_type, "VAL-012",
                f"{field} should be an integer if provided (got '{value}'). Field treated as missing.",
                IssueSeverity.warning, value, True
            ))
            return None

    def _make_issue(
        self, job: ImportJob, row_number: Optional[int], field_name: Optional[str],
        issue_type: IssueType, issue_code: str, message: str,
        severity: IssueSeverity, raw_value: Optional[str], record_included: bool
    ) -> ValidationIssue:
        return ValidationIssue(
            import_job_id=job.id,
            row_number=row_number,
            field_name=field_name,
            issue_type=issue_type,
            issue_code=issue_code,
            message=message,
            severity=severity,
            record_included=record_included,
            raw_value=raw_value,
        )
