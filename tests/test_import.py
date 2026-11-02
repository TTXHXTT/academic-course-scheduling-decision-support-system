"""
Data import and validation tests.
SRS Reference: FR-01, DR-01, DR-02
"""
import pytest
from app.services.import_service import ImportService
from app.models.dataset import DatasetStatus, IssueSeverity

VALID_CSV = b"""course_id,course_name,section_id,term,year,semester,days,times,modality,campus,enrollment,capacity,attempted_enrollment,unmet_demand,major,student_level
CS-101,Intro to CS,01,Fall 2023,2023,Fall,MWF,09:00-09:50,In-Person,San Bernardino,25,30,28,3,Computer Science,Freshman
CS-101,Intro to CS,02,Spring 2024,2024,Spring,TR,10:00-11:15,In-Person,San Bernardino,28,30,31,3,Computer Science,Freshman
MATH-200,Calculus,01,Fall 2023,2023,Fall,MWF,11:00-11:50,Online,San Bernardino,20,40,,,Mathematics,Sophomore
"""

MISSING_COURSE_ID_CSV = b"""course_id,course_name,section_id,term,year,semester,days,times,modality,campus,enrollment,capacity,attempted_enrollment,unmet_demand,major,student_level
,Missing Course,01,Fall 2023,2023,Fall,MWF,09:00-09:50,In-Person,SB,20,30,,,CS,Freshman
"""

NEGATIVE_ENROLLMENT_CSV = b"""course_id,course_name,section_id,term,year,semester,days,times,modality,campus,enrollment,capacity,attempted_enrollment,unmet_demand,major,student_level
CS-101,Test,01,Fall 2023,2023,Fall,MWF,09:00,In-Person,SB,-10,30,,,CS,Junior
"""

ENROLLMENT_EXCEEDS_CAPACITY_CSV = b"""course_id,course_name,section_id,term,year,semester,days,times,modality,campus,enrollment,capacity,attempted_enrollment,unmet_demand,major,student_level
CS-101,Test,01,Fall 2023,2023,Fall,MWF,09:00,In-Person,SB,35,30,,,CS,Junior
"""

EMPTY_CSV = b""
HEADER_ONLY_CSV = b"course_id,course_name,section_id,term,year,semester,days,times,modality,campus,enrollment,capacity,attempted_enrollment,unmet_demand,major,student_level\n"

DUPLICATE_CSV = b"""course_id,course_name,section_id,term,year,semester,days,times,modality,campus,enrollment,capacity,attempted_enrollment,unmet_demand,major,student_level
CS-101,Test,01,Fall 2023,2023,Fall,MWF,09:00,In-Person,SB,20,30,,,CS,Junior
CS-101,Test,01,Fall 2023,2023,Fall,MWF,09:00,In-Person,SB,20,30,,,CS,Junior
"""

INVALID_NUMERIC_CSV = b"""course_id,course_name,section_id,term,year,semester,days,times,modality,campus,enrollment,capacity,attempted_enrollment,unmet_demand,major,student_level
CS-101,Test,01,Fall 2023,2023,Fall,MWF,09:00,In-Person,SB,abc,xyz,,,CS,Junior
"""

MISSING_COLUMNS_CSV = b"""course_id,enrollment
CS-101,25
"""

PARTIAL_VALID_CSV = b"""course_id,course_name,section_id,term,year,semester,days,times,modality,campus,enrollment,capacity,attempted_enrollment,unmet_demand,major,student_level
CS-101,Good,01,Fall 2023,2023,Fall,MWF,09:00,In-Person,SB,25,30,,,CS,Junior
,Bad,02,Fall 2023,2023,Fall,MWF,09:00,In-Person,SB,20,30,,,CS,Junior
"""


class TestValidCSVImport:
    def test_imports_all_rows(self, db_session):
        service = ImportService(db_session)
        dataset, job = service.import_csv(VALID_CSV, "Test", "test.csv")
        assert job.status == "completed"
        assert job.total_rows == 3
        assert job.valid_rows == 3
        assert job.error_rows == 0

    def test_no_errors(self, db_session):
        service = ImportService(db_session)
        dataset, job = service.import_csv(VALID_CSV, "Test", "test.csv")
        errors = [i for i in job.validation_issues if i.severity == IssueSeverity.error]
        assert len(errors) == 0

    def test_optional_fields_are_none_not_zero(self, db_session):
        service = ImportService(db_session)
        dataset, job = service.import_csv(VALID_CSV, "Test", "test.csv")
        from app.models.course_record import CourseRecord
        record = db_session.query(CourseRecord).filter(
            CourseRecord.dataset_id == dataset.id, CourseRecord.course_id == "MATH-200"
        ).first()
        assert record is not None
        assert record.attempted_enrollment is None  # blank, NOT 0
        assert record.unmet_demand is None          # blank, NOT 0


class TestMissingRequiredFields:
    def test_missing_course_id_is_error(self, db_session):
        service = ImportService(db_session)
        dataset, job = service.import_csv(MISSING_COURSE_ID_CSV, "Test", "test.csv")
        assert job.error_rows >= 1
        codes = [i.issue_code for i in job.validation_issues if i.severity == IssueSeverity.error]
        assert "VAL-002" in codes

    def test_missing_course_id_row_excluded(self, db_session):
        service = ImportService(db_session)
        dataset, job = service.import_csv(MISSING_COURSE_ID_CSV, "Test", "test.csv")
        assert job.valid_rows == 0


class TestInvalidValues:
    def test_negative_enrollment_error(self, db_session):
        service = ImportService(db_session)
        dataset, job = service.import_csv(NEGATIVE_ENROLLMENT_CSV, "Test", "test.csv")
        codes = [i.issue_code for i in job.validation_issues if i.severity == IssueSeverity.error]
        assert "VAL-004" in codes

    def test_invalid_numeric_error(self, db_session):
        service = ImportService(db_session)
        dataset, job = service.import_csv(INVALID_NUMERIC_CSV, "Test", "test.csv")
        codes = [i.issue_code for i in job.validation_issues if i.severity == IssueSeverity.error]
        assert "VAL-010" in codes

    def test_enrollment_exceeds_capacity_is_warning_not_error(self, db_session):
        service = ImportService(db_session)
        dataset, job = service.import_csv(ENROLLMENT_EXCEEDS_CAPACITY_CSV, "Test", "test.csv")
        codes = [i.issue_code for i in job.validation_issues if i.severity == IssueSeverity.warning]
        assert "VAL-006" in codes
        assert job.valid_rows == 1  # Record retained


class TestEdgeCases:
    def test_empty_file(self, db_session):
        service = ImportService(db_session)
        dataset, job = service.import_csv(EMPTY_CSV, "Test", "test.csv")
        assert job.total_rows == 0
        assert len(job.validation_issues) > 0

    def test_header_only(self, db_session):
        service = ImportService(db_session)
        dataset, job = service.import_csv(HEADER_ONLY_CSV, "Test", "test.csv")
        assert job.total_rows == 0
        assert job.valid_rows == 0

    def test_duplicate_detected(self, db_session):
        service = ImportService(db_session)
        dataset, job = service.import_csv(DUPLICATE_CSV, "Test", "test.csv")
        codes = [i.issue_code for i in job.validation_issues if i.severity == IssueSeverity.warning]
        assert "VAL-008" in codes

    def test_missing_columns_fails(self, db_session):
        service = ImportService(db_session)
        dataset, job = service.import_csv(MISSING_COLUMNS_CSV, "Test", "test.csv")
        codes = [i.issue_code for i in job.validation_issues if i.severity == IssueSeverity.error]
        assert "VAL-001" in codes

    def test_partial_dataset_valid_rows_imported(self, db_session):
        service = ImportService(db_session)
        dataset, job = service.import_csv(PARTIAL_VALID_CSV, "Test", "test.csv")
        assert job.valid_rows == 1
        assert job.error_rows >= 1

    def test_no_silent_loss_of_rejected_records(self, db_session):
        service = ImportService(db_session)
        dataset, job = service.import_csv(PARTIAL_VALID_CSV, "Test", "test.csv")
        rejected = job.total_rows - job.valid_rows
        errors = len([i for i in job.validation_issues if i.severity == IssueSeverity.error])
        assert errors >= rejected
