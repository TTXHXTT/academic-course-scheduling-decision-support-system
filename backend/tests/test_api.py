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

