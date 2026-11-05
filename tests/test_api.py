"""
API endpoint tests - authentication, RBAC, datasets, analysis, scenarios.
SRS Reference: NFR-01, Section 12.C
"""
import pytest


class TestAuthentication:
    def test_login_success(self, test_client, auth_headers_admin):
        resp = test_client.get("/api/auth/me", headers=auth_headers_admin)
        assert resp.status_code == 200
        assert resp.json()["email"] == "admin@test.edu"

    def test_login_wrong_password(self, test_client, auth_headers_admin):
        resp = test_client.post("/api/auth/login", json={"email": "admin@test.edu", "password": "WrongPass"})
        assert resp.status_code == 401

    def test_login_unknown_user(self, test_client):
        resp = test_client.post("/api/auth/login", json={"email": "nobody@test.edu", "password": "Pass123"})
        assert resp.status_code == 401

    def test_unauthenticated_blocked(self, test_client):
        resp = test_client.get("/api/datasets/")
        assert resp.status_code == 401

    def test_me_returns_correct_role(self, test_client, auth_headers_admin):
        resp = test_client.get("/api/auth/me", headers=auth_headers_admin)
        assert resp.json()["role"] == "admin"


class TestRBAC:
    def test_scheduler_can_upload(self, test_client, auth_headers_scheduler):
        csv = b"course_id,course_name,section_id,term,year,semester,days,times,modality,campus,enrollment,capacity,attempted_enrollment,unmet_demand,major,student_level\nCS-101,Test,01,Fall 2023,2023,Fall,MWF,09:00,In-Person,SB,25,30,,,CS,Junior\n"
        resp = test_client.post("/api/datasets/upload", headers=auth_headers_scheduler,
            files={"file": ("test.csv", csv, "text/csv")},
            data={"name": "Test", "is_synthetic": "true"})
        assert resp.status_code == 200

    def test_coordinator_cannot_upload(self, test_client, db_engine):
        from sqlalchemy.orm import sessionmaker
        from app.core.security import hash_password
        from app.models.user import User, UserRole
        Session = sessionmaker(bind=db_engine)
        session = Session()
        if not session.query(User).filter(User.email == "coord@test.edu").first():
            u = User(email="coord@test.edu", hashed_password=hash_password("CoordPass123"), full_name="Coord", role=UserRole.program_coordinator, is_active=True)
            session.add(u)
            session.commit()
        session.close()
        login = test_client.post("/api/auth/login", json={"email": "coord@test.edu", "password": "CoordPass123"})
        token = login.json()["access_token"]
        headers = {"Authorization": f"Bearer {token}"}
        csv = b"course_id,term,enrollment,capacity\nCS-101,Fall 2023,25,30\n"
        resp = test_client.post("/api/datasets/upload", headers=headers,
            files={"file": ("test.csv", csv, "text/csv")}, data={"name": "Test", "is_synthetic": "true"})
        assert resp.status_code == 403

    def test_audit_requires_admin_or_chair(self, test_client, auth_headers_scheduler):
        resp = test_client.get("/api/audit/", headers=auth_headers_scheduler)
        assert resp.status_code == 403


class TestDatasetAPI:
    def _upload(self, client, headers, name="Test Dataset"):
        csv = b"course_id,course_name,section_id,term,year,semester,days,times,modality,campus,enrollment,capacity,attempted_enrollment,unmet_demand,major,student_level\nCS-101,Test,01,Fall 2023,2023,Fall,MWF,09:00,In-Person,SB,25,30,28,3,CS,Junior\nCS-101,Test,01,Fall 2022,2022,Fall,MWF,09:00,In-Person,SB,22,30,24,2,CS,Junior\n"
        resp = client.post("/api/datasets/upload", headers=headers,
            files={"file": ("test.csv", csv, "text/csv")}, data={"name": name, "is_synthetic": "true"})
        assert resp.status_code == 200
        return resp.json()["dataset_id"]

    def test_upload_and_list(self, test_client, auth_headers_scheduler):
        ds_id = self._upload(test_client, auth_headers_scheduler)
        resp = test_client.get("/api/datasets/", headers=auth_headers_scheduler)
        assert resp.status_code == 200
        assert len(resp.json()) == 1

    def test_non_csv_rejected(self, test_client, auth_headers_scheduler):
        resp = test_client.post("/api/datasets/upload", headers=auth_headers_scheduler,
            files={"file": ("test.xlsx", b"data", "application/vnd.ms-excel")},
            data={"name": "Bad", "is_synthetic": "true"})
        assert resp.status_code == 400


class TestAnalysisAPI:
    def _setup(self, client, headers):
        csv = b"course_id,course_name,section_id,term,year,semester,days,times,modality,campus,enrollment,capacity,attempted_enrollment,unmet_demand,major,student_level\nCS-101,Test,01,Fall 2023,2023,Fall,MWF,09:00,In-Person,SB,25,30,28,3,CS,Junior\nCS-101,Test,01,Fall 2022,2022,Fall,MWF,09:00,In-Person,SB,22,30,24,2,CS,Junior\n"
        ds = client.post("/api/datasets/upload", headers=headers,
            files={"file": ("t.csv", csv, "text/csv")}, data={"name": "Test", "is_synthetic": "true"})
        return ds.json()["dataset_id"]

    def test_run_analysis_completes(self, test_client, auth_headers_scheduler):
        ds_id = self._setup(test_client, auth_headers_scheduler)
        resp = test_client.post("/api/analysis/runs", headers=auth_headers_scheduler, json={"dataset_id": ds_id})
        assert resp.status_code == 200
        assert resp.json()["status"] == "completed"
        assert resp.json()["courses_analyzed"] >= 1

    def test_course_metrics_returned(self, test_client, auth_headers_scheduler):
        ds_id = self._setup(test_client, auth_headers_scheduler)
        run = test_client.post("/api/analysis/runs", headers=auth_headers_scheduler, json={"dataset_id": ds_id})
        run_id = run.json()["id"]
        courses = test_client.get(f"/api/analysis/runs/{run_id}/courses", headers=auth_headers_scheduler)
        assert courses.status_code == 200
        data = courses.json()
        assert len(data) >= 1
        assert data[0]["course_id"] == "CS-101"

    def test_analysis_endpoint_aliases_and_thresholds(self, test_client, auth_headers_scheduler):
        ds_id = self._setup(test_client, auth_headers_scheduler)
        # Test POST /api/analysis/run alias with custom parameters
        resp = test_client.post(
            "/api/analysis/run",
            headers=auth_headers_scheduler,
            json={
                "dataset_id": ds_id,
                "name": "Custom Threshold Test",
                "high_utilization_threshold": 90.0,
                "low_utilization_threshold": 45.0,
            }
        )
        assert resp.status_code == 200
        run_id = resp.json()["id"]

        # Test GET /api/analysis alias
        runs_list = test_client.get("/api/analysis", headers=auth_headers_scheduler)
        assert runs_list.status_code == 200
        assert any(r["id"] == run_id for r in runs_list.json())

        # Test GET /api/analysis/{run_id} alias
        single_run = test_client.get(f"/api/analysis/{run_id}", headers=auth_headers_scheduler)
        assert single_run.status_code == 200
        assert single_run.json()["name"] == "Custom Threshold Test"

        # Test GET /api/analysis/{run_id}/courses alias
        courses = test_client.get(f"/api/analysis/{run_id}/courses", headers=auth_headers_scheduler)
        assert courses.status_code == 200
        assert len(courses.json()) >= 1



class TestScenarioAPI:
    def _setup(self, client, headers):
        csv = b"course_id,course_name,section_id,term,year,semester,days,times,modality,campus,enrollment,capacity,attempted_enrollment,unmet_demand,major,student_level\nCS-101,Test,01,Fall 2022,2022,Fall,MWF,09:00,In-Person,SB,29,30,32,3,CS,Junior\nCS-101,Test,01,Fall 2023,2023,Fall,MWF,09:00,In-Person,SB,30,30,35,5,CS,Junior\n"
        ds = client.post("/api/datasets/upload", headers=headers,
            files={"file": ("t.csv", csv, "text/csv")}, data={"name": "ScenarioTest", "is_synthetic": "true"})
        run = client.post("/api/analysis/runs", headers=headers, json={"dataset_id": ds.json()["dataset_id"], "is_baseline": True})
        return run.json()["id"]

    def test_add_section_scenario(self, test_client, auth_headers_scheduler):
        run_id = self._setup(test_client, auth_headers_scheduler)
        resp = test_client.post("/api/scenarios/", headers=auth_headers_scheduler, json={
            "name": "Add Section",
            "baseline_analysis_id": run_id,
            "scenario_type": "add_section",
            "parameters": {"course_id": "CS-101", "capacity": 30, "term": "Fall 2024"},
        })
        assert resp.status_code == 200
        assert resp.json()["status"] == "completed"
        assert len(resp.json()["results"]) > 0

    def test_scenario_results_are_simulated(self, test_client, auth_headers_scheduler):
        run_id = self._setup(test_client, auth_headers_scheduler)
        resp = test_client.post("/api/scenarios/", headers=auth_headers_scheduler, json={
            "name": "Capacity Test",
            "baseline_analysis_id": run_id,
            "scenario_type": "change_capacity",
            "parameters": {"course_id": "CS-101", "new_capacity": 50},
        })
        import json
        results = resp.json()["results"]
        affected = [r for r in results if r["is_affected"]]
        for r in affected:
            if r["scenario_value_json"]:
                sv = json.loads(r["scenario_value_json"])
                assert sv.get("is_simulated") is True

    def test_invalid_scenario_type_rejected(self, test_client, auth_headers_scheduler):
        run_id = self._setup(test_client, auth_headers_scheduler)
        resp = test_client.post("/api/scenarios/", headers=auth_headers_scheduler, json={
            "name": "Bad", "baseline_analysis_id": run_id,
            "scenario_type": "invalid_xyz", "parameters": {},
        })
        assert resp.status_code == 422


class TestHTMLPages:
    def test_login_page_renders(self, test_client):
        resp = test_client.get("/login")
        assert resp.status_code == 200
        assert "ACS Portal Sign In" in resp.text

    def test_dashboard_page_renders(self, test_client):
        resp = test_client.get("/dashboard")
        assert resp.status_code == 200
        assert "Executive Dashboard" in resp.text

    def test_imports_page_renders(self, test_client):
        resp = test_client.get("/imports")
        assert resp.status_code == 200
        assert "Historical Academic Data Import" in resp.text

    def test_explorer_page_renders(self, test_client):
        resp = test_client.get("/explorer")
        assert resp.status_code == 200
        assert "Historical Course Explorer" in resp.text

    def test_analysis_page_renders(self, test_client):
        resp = test_client.get("/analysis")
        assert resp.status_code == 200
        assert "Course Demand Analysis Engine" in resp.text

    def test_recommendations_page_renders(self, test_client):
        resp = test_client.get("/recommendations")
        assert resp.status_code == 200
        assert "Course-Offering Decision Support" in resp.text

    def test_scenarios_page_renders(self, test_client):
        resp = test_client.get("/scenarios")
        assert resp.status_code == 200
        assert "What-If Course Offering Scenarios" in resp.text

    def test_history_page_renders(self, test_client):
        resp = test_client.get("/history")
        assert resp.status_code == 200
        assert "Analysis History & Run Traceability" in resp.text

    def test_audit_page_renders(self, test_client):
        resp = test_client.get("/audit")
        assert resp.status_code == 200
        assert "Administrative Audit Trail" in resp.text

    def test_student_schedule_page_renders(self, test_client):
        resp = test_client.get("/student/schedule")
        assert resp.status_code == 200
        assert "Student Class Schedule &amp; Registration" in resp.text or "Student Class Schedule" in resp.text


class TestStudentSchedule:
    def test_student_can_login_with_email_and_id(self, test_client, db_engine):
        from sqlalchemy.orm import sessionmaker
        from app.models.user import User, UserRole
        from app.core.security import hash_password
        Session = sessionmaker(bind=db_engine)
        session = Session()
        stu = User(
            email="007455611@coyote.csusb.edu",
            student_id="007455611",
            hashed_password=hash_password("123456"),
            full_name="Student Coyote",
            role=UserRole.student,
            is_active=True,
        )
        session.add(stu)
        session.commit()
        session.close()

        # Login with student email
        resp1 = test_client.post("/api/auth/login", json={"email": "007455611@coyote.csusb.edu", "password": "123456"})
        assert resp1.status_code == 200
        assert resp1.json()["user"]["role"] == "student"

        # Login with student ID
        resp2 = test_client.post("/api/auth/login", json={"email": "007455611", "password": "123456"})
        assert resp2.status_code == 200
        assert resp2.json()["user"]["role"] == "student"

    def test_student_add_and_view_class_schedule(self, test_client, db_engine):
        from sqlalchemy.orm import sessionmaker
        from app.models.user import User, UserRole
        from app.models.dataset import Dataset
        from app.models.course_record import CourseRecord
        from app.core.security import hash_password
        Session = sessionmaker(bind=db_engine)
        session = Session()
        stu = User(
            email="001234567@coyote.csusb.edu",
            student_id="001234567",
            hashed_password=hash_password("123456"),
            full_name="Alice Student",
            role=UserRole.student,
            is_active=True,
        )
        session.add(stu)
        session.flush()

        ds = Dataset(name="current_courses", source_filename="courses.csv", is_synthetic=True, row_count=1, valid_row_count=1)
        session.add(ds)
        session.flush()

        course = CourseRecord(
            dataset_id=ds.id,
            course_id="CSE-2010",
            course_name="Computer Science I",
            section_id="01",
            term="Fall 2026",
            days="MWF",
            times="10:00-10:50",
            modality="In-Person",
            campus="San Bernardino",
            enrollment=25,
            capacity=30,
        )
        session.add(course)
        session.commit()
        course_id = course.id
        session.close()

        # Login as student
        login_resp = test_client.post("/api/auth/login", json={"email": "001234567", "password": "123456"})
        token = login_resp.json()["access_token"]
        headers = {"Authorization": f"Bearer {token}"}

        # Add course to schedule
        add_resp = test_client.post("/api/student/schedule/add", headers=headers, json={"course_record_id": course_id})
        assert add_resp.status_code == 201
        added_data = add_resp.json()
        assert added_data["course_id"] == "CSE-2010"
        assert added_data["course_name"] == "Computer Science I"
        assert added_data["days"] == "MWF"
        assert added_data["times"] == "10:00-10:50"
        assert added_data["modality"] == "In-Person"

        # View schedule
        sched_resp = test_client.get("/api/student/schedule", headers=headers)
        assert sched_resp.status_code == 200
        sched_data = sched_resp.json()
        assert sched_data["total_classes"] == 1
        c_info = sched_data["classes"][0]
        assert c_info["course_id"] == "CSE-2010"
        assert c_info["section_id"] == "01"
        assert c_info["times"] == "10:00-10:50"

        # Drop course
        drop_resp = test_client.delete(f"/api/student/schedule/{c_info['schedule_id']}", headers=headers)
        assert drop_resp.status_code == 204


