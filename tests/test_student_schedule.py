"""
Tests for Student Schedule operations: Add Class, Drop Class, and Modify Schedule.
"""
import pytest
from app.core.security import hash_password
from app.models.user import User, UserRole
from app.models.dataset import Dataset
from app.models.course_record import CourseRecord
from app.models.student_schedule import StudentSchedule


@pytest.fixture
def student_user_and_auth(db_session, test_client):
    """Creates a student and returns auth headers."""
    student = User(
        email="007455611@coyote.csusb.edu",
        student_id="007455611",
        hashed_password=hash_password("123456"),
        full_name="Jane Coyote",
        role=UserRole.student,
        is_active=True,
    )
    db_session.add(student)
    db_session.commit()

    login_res = test_client.post("/api/auth/login", json={"email": "007455611", "password": "123456"})
    assert login_res.status_code == 200
    token = login_res.json()["access_token"]
    headers = {"Authorization": f"Bearer {token}"}
    return student, headers


@pytest.fixture
def sample_courses(db_session, student_user_and_auth):
    """Seeds sample course records for scheduling tests."""
    student, _ = student_user_and_auth
    ds = Dataset(
        name="current_courses",
        description="Current test dataset",
        imported_by_id=student.id,
        is_synthetic=True,
        row_count=4,
        valid_row_count=4,
    )
    db_session.add(ds)
    db_session.commit()
    db_session.refresh(ds)

    c1 = CourseRecord(
        dataset_id=ds.id,
        course_id="CSE-2010",
        course_name="Computer Science I",
        section_id="01",
        term="Fall 2026",
        days="MW",
        times="10:00-11:15",
        modality="In-Person",
        campus="San Bernardino",
        capacity=30,
        enrollment=25,
    )
    c2 = CourseRecord(
        dataset_id=ds.id,
        course_id="CSE-2010",
        course_name="Computer Science I",
        section_id="02",
        term="Fall 2026",
        days="TR",
        times="14:00-15:15",
        modality="In-Person",
        campus="San Bernardino",
        capacity=30,
        enrollment=18,
    )
    c3_conflicting = CourseRecord(
        dataset_id=ds.id,
        course_id="MATH-2210",
        course_name="Calculus I",
        section_id="01",
        term="Fall 2026",
        days="MWF",
        times="10:30-11:45",  # Overlaps with CSE-2010 Sec 01 on MW
        modality="In-Person",
        campus="San Bernardino",
        capacity=35,
        enrollment=30,
    )
    c4_no_conflict = CourseRecord(
        dataset_id=ds.id,
        course_id="ENG-1070",
        course_name="First Year Writing",
        section_id="01",
        term="Fall 2026",
        days="TR",
        times="09:00-10:15",
        modality="In-Person",
        campus="San Bernardino",
        capacity=25,
        enrollment=20,
    )
    c5_full = CourseRecord(
        dataset_id=ds.id,
        course_id="PSYC-1100",
        course_name="Introduction to Psychology",
        section_id="01",
        term="Fall 2026",
        days="F",
        times="13:00-15:45",
        modality="In-Person",
        campus="San Bernardino",
        capacity=30,
        enrollment=30,  # Full / at capacity
    )
    db_session.add_all([c1, c2, c3_conflicting, c4_no_conflict, c5_full])
    db_session.commit()
    for c in [c1, c2, c3_conflicting, c4_no_conflict, c5_full]:
        db_session.refresh(c)
    return {"c1": c1, "c2": c2, "conflict": c3_conflicting, "free": c4_no_conflict, "full": c5_full}


def test_browse_classes(test_client, student_user_and_auth, sample_courses):
    _, headers = student_user_and_auth
    res = test_client.get("/api/student/classes?search=CSE", headers=headers)
    assert res.status_code == 200
    data = res.json()
    assert len(data) >= 2
    assert all("CSE" in d["course_id"] for d in data)


def test_get_course_sections(test_client, student_user_and_auth, sample_courses):
    _, headers = student_user_and_auth
    res = test_client.get("/api/student/classes/CSE-2010/sections", headers=headers)
    assert res.status_code == 200
    sections = res.json()
    assert len(sections) == 2
    section_ids = [s["section_id"] for s in sections]
    assert "01" in section_ids
    assert "02" in section_ids


def test_add_class_and_view_schedule(test_client, student_user_and_auth, sample_courses):
    _, headers = student_user_and_auth
    c1 = sample_courses["c1"]

    # 1. Add class
    add_res = test_client.post(
        "/api/student/schedule/add",
        json={"course_record_id": c1.id, "grade_mode": "Letter Grade", "notes": "Core CS Req"},
        headers=headers,
    )
    assert add_res.status_code == 201
    item = add_res.json()
    assert item["course_id"] == "CSE-2010"
    assert item["section_id"] == "01"
    assert item["status"] == "Enrolled"
    assert item["grade_mode"] == "Letter Grade"
    assert item["notes"] == "Core CS Req"

    # 2. Duplicate add rejection
    dup_res = test_client.post(
        "/api/student/schedule/add",
        json={"course_record_id": c1.id},
        headers=headers,
    )
    assert dup_res.status_code == 400

    # 3. View schedule
    sched_res = test_client.get("/api/student/schedule", headers=headers)
    assert sched_res.status_code == 200
    sched = sched_res.json()
    assert sched["total_classes"] == 1
    assert sched["classes"][0]["course_id"] == "CSE-2010"


def test_add_class_conflict_detection(test_client, student_user_and_auth, sample_courses):
    _, headers = student_user_and_auth
    c1 = sample_courses["c1"]
    c_conflict = sample_courses["conflict"]

    # Enroll in c1 (MW 10:00-11:15)
    test_client.post(
        "/api/student/schedule/add",
        json={"course_record_id": c1.id},
        headers=headers,
    )

    # Attempt to enroll in conflicting c3 (MWF 10:30-11:45) without allow_conflict
    res_conflict = test_client.post(
        "/api/student/schedule/add",
        json={"course_record_id": c_conflict.id},
        headers=headers,
    )
    assert res_conflict.status_code == 409
    assert "Time conflict detected" in res_conflict.json()["detail"]

    # Now enroll with allow_conflict=true
    res_override = test_client.post(
        "/api/student/schedule/add?allow_conflict=true",
        json={"course_record_id": c_conflict.id},
        headers=headers,
    )
    assert res_override.status_code == 201


def test_drop_class_only_no_modify(test_client, student_user_and_auth, sample_courses):
    """Confirms the PUT /schedule/:id endpoint is removed — only add and drop are allowed."""
    _, headers = student_user_and_auth
    c1 = sample_courses["c1"]

    add_res = test_client.post(
        "/api/student/schedule/add",
        json={"course_record_id": c1.id},
        headers=headers,
    )
    sched_id = add_res.json()["schedule_id"]

    # PUT (modify) must return 405 Method Not Allowed since it was removed
    mod_res = test_client.put(
        f"/api/student/schedule/{sched_id}",
        json={"grade_mode": "Audit"},
        headers=headers,
    )
    assert mod_res.status_code == 405


def test_drop_class(test_client, student_user_and_auth, sample_courses):
    _, headers = student_user_and_auth
    c1 = sample_courses["c1"]

    add_res = test_client.post(
        "/api/student/schedule/add",
        json={"course_record_id": c1.id},
        headers=headers,
    )
    sched_id = add_res.json()["schedule_id"]

    # Drop class
    drop_res = test_client.delete(f"/api/student/schedule/{sched_id}", headers=headers)
    assert drop_res.status_code == 204

    # Verify schedule is now empty
    sched_res = test_client.get("/api/student/schedule", headers=headers)
    assert sched_res.status_code == 200
    assert sched_res.json()["total_classes"] == 0

    # Drop non-existent returns 404
    drop_again = test_client.delete(f"/api/student/schedule/{sched_id}", headers=headers)
    assert drop_again.status_code == 404


def test_add_waitlist_when_capacity_reached(test_client, student_user_and_auth, sample_courses):
    """When a course is full (enrollment >= capacity), registering adds student as Waitlisted."""
    _, headers = student_user_and_auth
    c_full = sample_courses["full"]

    res = test_client.post(
        "/api/student/schedule/add",
        json={"course_record_id": c_full.id},
        headers=headers,
    )
    assert res.status_code == 201
    item = res.json()
    assert item["status"] == "Waitlisted"
    assert item["course_id"] == "PSYC-1100"

    # In my schedule, it shows status Waitlisted
    sched_res = test_client.get("/api/student/schedule", headers=headers)
    assert sched_res.status_code == 200
    sched = sched_res.json()
    assert sched["classes"][0]["status"] == "Waitlisted"

    # Dropping waitlist works
    drop_res = test_client.delete(f"/api/student/schedule/{item['schedule_id']}", headers=headers)
    assert drop_res.status_code == 204


def test_student_pages_accessible(test_client):
    """Verifies student HTML pages render 200."""
    res_sched = test_client.get("/student/schedule")
    assert res_sched.status_code == 200
    assert "My Class Schedule" in res_sched.text

    res_add = test_client.get("/student/add-classes")
    assert res_add.status_code == 200
    assert "Course Catalog & Class Registration" in res_add.text

